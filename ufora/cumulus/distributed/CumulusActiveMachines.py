#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import logging
import Queue
import threading
import traceback
import time
import ufora.native.Json as NativeJson
import ufora.native.SharedState as SharedStateNative
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.AsyncView as AsyncView
import ufora.distributed.Stoppable as Stoppable
import ufora.util.ManagedThread as ManagedThread

class CumulusActiveMachinesListener(object):
    """Base class for clients listening to CumulusActiveMachines"""

    def onWorkerAdd(self, ip, ports, machineIdAsString):
        """A worker with hash 'worker' was added at ip and ports."""
        assert False, "subclasses implement"

    def onWorkerDrop(self, machineIdAsString):
        """A worker with hash 'worker' dropped out of the cluster."""
        assert False, "subclasses implement"

    def onReconnectedToSharedState(self):
        """We reconnected to SharedState."""
        assert False, "Subclasses implement"

TIME_TO_SLEEP_AFTER_RECONNECT = 5

class CumulusActiveMachines(Stoppable.Stoppable):
    """Class for maintaining a list of active cumulus nodes.

    Adding listeners starts the CumulusActiveMachines background loop. Removing the last
    listener stops it.
    """
    def __init__(self, viewFactory):
        Stoppable.Stoppable.__init__(self)
        self.viewFactory = viewFactory
        self.activeMachineIds = set()
        self._outgoingNotifications = Queue.Queue()
        self._lock = threading.RLock()
        self._lastDisconnectTime = None
        self._lastReconnectTime = None
        self._registeredIpPortAndMachineId = None


        logging.info(
            "CumulusActiveMachines connecting to shared state: %s",
            viewFactory
            )

        self.listeners_ = set()
        self.clientID = None

        self.isConnected = False
        self.isConnecting = False
        self.disconnectedWhileConnecting = False


        self._triggerUpdateAfterDisconnectThreads = []

        self.clientIdToIpPortAndMachineIdAsString = {}
        self.machineIdToClientId = {}

        self.workerStatusKeyspace = SharedState.Keyspace(
            "ComparisonKeyType",
            NativeJson.Json((('P', 'CumulusNodeStatus'),)),
            1
            )

        self.asyncView = None

        self.eventLoopThread = ManagedThread.ManagedThread(target = self.eventDispatchLoop)

    reconnectViewOnDisconnectIntervalForTesting = None

    def updateActiveMachinesOnReactorThread(self):
        self.asyncView.reactorThreadCall(self.updateActiveMachines)

    def ownMachineIdAsString(self):
        if self._registeredIpPortAndMachineId is not None:
            return self._registeredIpPortAndMachineId[2]
        else:
            return None

    def clientIdToMachineIdAsString(self, client):
        if client in self.clientIdToIpPortAndMachineIdAsString:
            return self.clientIdToIpPortAndMachineIdAsString[client][2]
        else:
            return None

    def updateActiveMachines(self):
        if self.shouldStop():
            return

        if self._lastDisconnectTime is not None:
            if self._lastReconnectTime is None:
                return

            if time.time() - self._lastReconnectTime < TIME_TO_SLEEP_AFTER_RECONNECT:
                #we need to defer until later
                return

        logging.debug('%s attempting to get introspection information', self.clientID)
        try:
            introspectionInfo = self.asyncView.keyspaceItems(SharedStateNative.getClientInfoKeyspace())
        except UserWarning:
            logging.info('AsyncView received exception from View:\n%s', traceback.format_exc())
            self.setDisconnected()
            raise

        currentlyConnectedClientIds = set([key[1].toSimple() for key, value in introspectionInfo if value.toSimple() != 'disconnected'])

        currentlyConnectedWorkers = set()
        for clientId in currentlyConnectedClientIds:
            machineId = self.clientIdToMachineIdAsString(clientId)
            if machineId:
                currentlyConnectedWorkers.add(machineId)

        logging.debug('%s currently connected list is %s', self.ownMachineIdAsString, currentlyConnectedWorkers)

        with self._lock:
            for deadWorker in self.activeMachineIds - currentlyConnectedWorkers:
                if deadWorker != self.ownMachineIdAsString():
                    logging.info("Worker dropped: %s which is not our ID (%s)", deadWorker, self.ownMachineIdAsString())
                    self.activeMachineIds.remove(deadWorker)

                    if deadWorker not in self.machineIdToClientId:
                        logging.critical("Worker %s is dead, but I don't have a client id for it.", deadWorker)
                        assert False
                    else:
                        deadClientID = self.machineIdToClientId[deadWorker]
                        self.onWorkerDrop(deadClientID, *self.clientIdToIpPortAndMachineIdAsString[deadClientID])

        newlyAliveClientIds = []
        with self._lock:
            for newlyAliveClientId in set(self.clientIdToIpPortAndMachineIdAsString.keys()).intersection(currentlyConnectedClientIds):
                nowAliveMachineId = self.clientIdToMachineIdAsString(newlyAliveClientId)

                if nowAliveMachineId is not None and nowAliveMachineId not in self.activeMachineIds:
                    logging.info(
                            "Worker clientId=%s added with IP %s and ports %s, machineIdAsString=%s",
                            nowAliveMachineId,
                            *self.clientIdToIpPortAndMachineIdAsString[newlyAliveClientId]
                            )
                    self.activeMachineIds.add(nowAliveMachineId)

                    # Defer onWorkerAdd notifications.
                    newlyAliveClientIds.append(newlyAliveClientId)
                    logging.debug("Active workers: %s", self.activeMachineIds)

        for newlyAliveClientId in newlyAliveClientIds:
            self.onWorkerAdd(newlyAliveClientId, *self.clientIdToIpPortAndMachineIdAsString[newlyAliveClientId])

    def onNewWorkerStatus(self, items):
        """A key in the worker status space changed"""
        for key, value in items.iteritems():
            logging.debug("Updating status for key %s", key)

            clientId = key[0].toSimple()
            ipAndPortAndMachineIdHash = value.toSimple()

            try:
                ip, ports, machineIdAsString = ipAndPortAndMachineIdHash
                ports = [int(p) for p in ports]

                with self._lock:
                    self.clientIdToIpPortAndMachineIdAsString[clientId] = (ip,ports,machineIdAsString)
                    self.machineIdToClientId[machineIdAsString] = clientId
            except:
                ports = None
                ip = None
                logging.error("an invalid ip/ports entry was placed in "
                    + " the CumulusService shared state table: %s", ipAndPortAndMachineIdHash)

        self.updateActiveMachines()

    def onNewClientInfo(self, items):
        self.updateActiveMachines()

    def addListener(self, listener):
        with self._lock:
            self.listeners_.add(listener)
            for workerClientID in self.activeMachineIds:
                self.onWorkerAdd(workerClientID, *self.clientIdToIpPortAndMachineIdAsString[workerClientID])

    def dropListener(self, listener):
        shouldStop = False
        with self._lock:
            if listener in self.listeners_:
                self.listeners_.remove(listener)
                if len(self.listeners_) == 0:
                    shouldStop = True
        if shouldStop:
            self.stop()

    def clearOutgoingNotificationsQueue(self):
        while True:
            try:
                self._outgoingNotifications.get_nowait()
            except Queue.Empty:
                # put a (None, None) pair in the queue to wake up the event loop
                # if it is blocked on getting from the queue
                self._outgoingNotifications.put( (None, None) )
                return

        self._outgoingNotifications.put( (None, None) )

    def stopService(self):
        logging.debug("CumulusActiveMachines tearing down")
        Stoppable.Stoppable.stop(self)

        self.asyncView.stopService()
        self.clearOutgoingNotificationsQueue()

        if threading.currentThread() != self.eventLoopThread:
            logging.debug('tearing down eventLoopThread')
            self.eventLoopThread.join()
        else:
            logging.debug('not joining because this is being called from its own thread')

        logging.debug("CumulusActiveMachines torn down")

        with self._lock:
            threadsToJoin = self._triggerUpdateAfterDisconnectThreads
            self._triggerUpdateAfterDisconnectThreads = []

        logging.debug("Joining %s threads: ", len(threadsToJoin))
        for t in threadsToJoin:
            t.join()
            threadsToJoin.remove(t)

    def registerSelfAsActive(self, address, ports, machineIdAsString):
        '''push information about this CumulusActiveMachine into SharedState'''
        assert self.asyncView is None, "Can't call registerSelfAsActive after we've started the service"

        self._registeredIpPortAndMachineId = (address, ports, machineIdAsString)

    def writeOwnRegistrationInformationIntoView_(self):
        if self._registeredIpPortAndMachineId is None:
            return

        address, ports, machineIdAsString = self._registeredIpPortAndMachineId

        logging.info(
            "CumulusActiveMachine registering worker %s at %s:%s with id %s",
            self.clientID,
            address,
            ports,
            machineIdAsString
            )

        with self._lock:
            self.activeMachineIds.add(machineIdAsString)

        key = SharedState.Key(self.workerStatusKeyspace, (NativeJson.Json(str(self.clientID)),))
        value = NativeJson.Json( (str(address), [str(x) for x in ports], machineIdAsString) )

        doneWithCall = threading.Event()
        self.asyncView.pushTransaction(key, value, lambda result: doneWithCall.set())

        while not doneWithCall.wait(.1) and not self._stopFlag.is_set():
            logging.debug('CumulusActiveMachines waiting on registerSelfAsActive')

    def startService(self):
        """start all background thread processes"""
        logging.debug("CumulusActiveMachines starting update loop")
        self.eventLoopThread.start()

        self.connectView()

    def connectView(self):
        try:
            succeeded = False

            logging.info(
                "CumulusActiveMachines connecting to sharedState. %s",
                self._registeredIpPortAndMachineId or ""
                )

            with self._lock:
                assert not self.isConnected
                assert not self.isConnecting
                self.isConnecting = True

            connected = threading.Event()

            def onConnect(value):
                self.clientID = self.asyncView.id
                connected.set()
                logging.info(
                        "CumulusActiveMachines created SharedState view with client id %s",
                        str(self.clientID)
                        )

            if self.asyncView is not None:
                self.asyncView.stopService()

            self.asyncView = AsyncView.AsyncView(self.viewFactory,
                                                 onConnectCallback=onConnect,
                                                 onErrorCallback=self._onAsyncViewError)
            self.asyncView.startService()

            while not self.shouldStop() and not connected.wait(.1):
                logging.debug('waiting for view to connect')

            if CumulusActiveMachines.reconnectViewOnDisconnectIntervalForTesting is not None:
                time.sleep(CumulusActiveMachines.reconnectViewOnDisconnectIntervalForTesting)

            done = threading.Event()

            def subscribeCallback(result):
                done.set()

            def subscribe():
                try:
                    self.asyncView.subscribeToKeyspace(SharedStateNative.getClientInfoKeyspace(), 1, self.onNewClientInfo)
                    doneDeferred = self.asyncView.subscribeToKeyspace(self.workerStatusKeyspace, 0, self.onNewWorkerStatus)
                    doneDeferred.addCallbacks(subscribeCallback, lambda exception : None)
                except UserWarning as ex:
                    logging.warn("Failed to subscribe to asyncView keyspace because we disconnected from shared state while reconnecting to shared state")

            self.asyncView.reactorThreadCall(subscribe)
            while not self._stopFlag.is_set() and not done.wait(.1) and not self.disconnectedWhileConnecting:
                logging.debug('CumulusActiveMachines is waiting on the subscription')

            self.writeOwnRegistrationInformationIntoView_()

            self._lastReconnectTime = time.time()

            succeeded = True
        except UserWarning as ex:
            logging.warn("Exception thrown during connect view, because we disconnected while reconnecting")
        finally:
            wantsToReconnect = False
            with self._lock:
                self.isConnected = True
                self.isConnecting = False

                if self.disconnectedWhileConnecting:
                    wantsToReconnect = True
                    self.isConnected = False
                    self.disconnectedWhileConnecting = False

            if wantsToReconnect:
                #we disconnected while we were connecting. Lets try again!
                self.connectView()
            else:
                def invokeReconnectedToSharedState(listener):
                    try:
                        listener.onReconnectedToSharedState()
                    except:
                        logging.error(
                                "Failed to notify listener of onReconnectedToSharedState: %s",
                                traceback.format_exc()
                                )

                with self._lock:
                    for listener in self.listeners_:
                        self._outgoingNotifications.put( (listener, invokeReconnectedToSharedState) )

    def _onAsyncViewError(self, error):
        if isinstance(error, AsyncView.Disconnected):
            self.setDisconnected()

    def setDisconnected(self):
        logging.warn("SharedState is disconnected from CAM. Trying to reconnect.")
        with self._lock:
            self._lastDisconnectTime = time.time()
            self._lastReconnectTime = None
            self.isConnected = False

            def sleepAndTriggerUpdate():
                while (not self.shouldStop() and (
                        self._lastReconnectTime is None or
                            time.time() <= self._lastReconnectTime + TIME_TO_SLEEP_AFTER_RECONNECT + 0.01)
                        ):
                    time.sleep(0.01)

                self.updateActiveMachinesOnReactorThread()

            newThread = ManagedThread.ManagedThread(target = sleepAndTriggerUpdate)

            with self._lock:
                self._triggerUpdateAfterDisconnectThreads.append(newThread)

            newThread.start()

            if self.isConnecting:
                logging.warn("CAM disconnected from SharedState while connecting. Setting a flag and sleeping.")
                self.disconnectedWhileConnecting = True
                connectDirectly = False
            else:
                connectDirectly = True


        if connectDirectly:
            self.connectView()

    def onWorkerAdd(self, clientId, ip, ports, machineIdAsString):
        def invokeOnWorkerAdd(listener):
            try:
                listener.onWorkerAdd(ip, ports, machineIdAsString)
            except:
                logging.error(
                        "Failed to notify listener of added worker: %s",
                        traceback.format_exc()
                        )

        with self._lock:
            for listener in self.listeners_:
                self._outgoingNotifications.put( (listener, invokeOnWorkerAdd) )

    def onWorkerDrop(self, worker, ip, ports, machineIdAsString):
        del self.machineIdToClientId[machineIdAsString]

        def invokeOnWorkerDrop(listener):
            try:
                listener.onWorkerDrop(machineIdAsString)
            except:
                logging.error(
                    "Listener raised exception in onWorkerDrop: %s",
                    traceback.format_exc()
                    )

        with self._lock:
            for listener in self.listeners_:
                self._outgoingNotifications.put( (listener, invokeOnWorkerDrop) )

    def eventDispatchLoop(self):
        logging.debug("Event dispatch loop started")
        while not self.shouldStop():
            try:
                listener, callback = self._outgoingNotifications.get(block=True, timeout=0.5)
                if listener is not None:
                    callback(listener)
            except Queue.Empty:
                logging.debug("outgoing notifications queue is empty")



