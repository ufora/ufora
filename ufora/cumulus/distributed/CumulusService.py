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

"""Implements a service for Cumulus and a socket protocol to connect to it."""

import logging
import os
import shutil
import threading
import time
import uuid

import ufora

import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager

import ufora.distributed.Stoppable as Stoppable
import ufora.util.ManagedThread as ManagedThread
import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines
import ufora.cumulus.distributed.PythonIoTaskService as PythonIoTaskService

import ufora.native.Cumulus as CumulusNative
import ufora.native.Hash as Hash

import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.ModuleImporter as ModuleImporter

import traceback

HANDSHAKE_TIMEOUT = 20.0


class CumulusService(Stoppable.Stoppable):
    def __init__(self,
                 ownAddress,
                 channelListener,
                 channelFactory,
                 eventHandler,
                 callbackScheduler,
                 diagnosticsDir,
                 config,
                 viewFactory,
                 s3InterfaceFactory=None,
                 objectStore=None):
        Stoppable.Stoppable.__init__(self)

        #acquire a machineId randomly, using uuid
        self.machineId = CumulusNative.MachineId(
            Hash.Hash.sha1(str(uuid.uuid4()))
            )

        self.ownAddress = ownAddress
        self.callbackScheduler = callbackScheduler
        self.viewFactory = viewFactory
        self.s3InterfaceFactory = s3InterfaceFactory
        self.objectStore = objectStore
        self.threadsStarted_ = False
        self.connectedMachines = set()
        self.connectingMachines = set()  # machines we are in the process of connecting to
        self.droppedMachineIds = set()
        self.lock = threading.RLock()
        self.cumulusMaxRamCacheSizeOverride = config.cumulusMaxRamCacheMB * 1024*1024
        self.cumulusVectorRamCacheSizeOverride = config.cumulusVectorRamCacheMB * 1024*1024
        self.cumulusThreadCountOverride = config.cumulusServiceThreadCount
        self.cumulusTrackTcmalloc = config.cumulusTrackTcmalloc
        self.eventHandler = eventHandler

        self.reconnectPersistentCacheIndexViewThreads = []

        if config.cumulusDiskCacheStorageSubdirectory is not None:
            self.cumulusDiskCacheWantsDeletionOnTeardown = True
            self.cumulusDiskCacheStorageDir = os.path.join(
                config.cumulusDiskCacheStorageDir,
                config.cumulusDiskCacheStorageSubdirectory
                )
        else:
            self.cumulusDiskCacheWantsDeletionOnTeardown = False
            self.cumulusDiskCacheStorageDir = config.cumulusDiskCacheStorageDir

        self._stopEvent = threading.Event()

        self._channelListener = channelListener
        assert len(self._channelListener.ports) == 2
        self._channelFactory = channelFactory

        Runtime.initialize()
        ModuleImporter.initialize()

        self.cumulusActiveMachines = CumulusActiveMachines.CumulusActiveMachines(
            self.viewFactory
            )

        self.cumulusChannelFactoryThread = ManagedThread.ManagedThread(
            target=self._channelListener.start
            )

        self.vdm = VectorDataManager.constructVDM(
            callbackScheduler,
            self.cumulusVectorRamCacheSizeOverride,
            self.cumulusMaxRamCacheSizeOverride
            )

        if self.cumulusTrackTcmalloc:
            self.vdm.getMemoryManager().enableCountTcMallocMemoryAsEcMemory()

        self.persistentCacheIndex = CumulusNative.PersistentCacheIndex(
            viewFactory.createView(retrySeconds=10.0, numRetries=10),
            callbackScheduler
            )

        self.vdm.setPersistentCacheIndex(self.persistentCacheIndex)

        self.deleteCumulusDiskCacheIfNecessary()

        self.offlineCache = CumulusNative.DiskOfflineCache(
            callbackScheduler,
            self.cumulusDiskCacheStorageDir,
            config.cumulusDiskCacheStorageMB * 1024 * 1024,
            config.cumulusDiskCacheStorageFileCount
            )

        checkpointInterval = config.cumulusCheckpointIntervalSeconds
        if checkpointInterval == 0:
            checkpointPolicy = CumulusNative.CumulusCheckpointPolicy.None()
        else:
            checkpointPolicy = CumulusNative.CumulusCheckpointPolicy.Periodic(
                checkpointInterval,
                1024 * 1024
                )

        self.cumulusWorker = self.constructCumlusWorker(
            callbackScheduler,
            CumulusNative.CumulusWorkerConfiguration(
                self.machineId,
                self.cumulusThreadCountOverride,
                checkpointPolicy,
                ExecutionContext.createContextConfiguration(),
                diagnosticsDir or ""
                ),
            self.vdm,
            self.offlineCache,
            eventHandler
            )

        self.datasetLoadService = None
        if self.s3InterfaceFactory:
            externalDatasetChannel = self.cumulusWorker.getExternalDatasetRequestChannel(
                callbackScheduler
                )
            self.datasetLoadService = PythonIoTaskService.PythonIoTaskService(
                self.s3InterfaceFactory,
                self.objectStore,
                self.vdm,
                externalDatasetChannel.makeQueuelike(callbackScheduler)
                )

        self.cumulusWorker.startComputations()

        if self.datasetLoadService:
            self.datasetLoadService.startService()

    @staticmethod
    def constructCumlusWorker(*args):
        # boost::python wrapper for CumulusWorker can't handle a None
        # eventHandler. We must call the overload without that argument.
        if args[-1] is None:
            args = args[:-1]
        return CumulusNative.CumulusWorker(*args)


    def stopService(self):
        self.teardown()

    def teardown(self):
        logging.debug('calling teardown from %s', ''.join(traceback.format_stack()))
        with self.lock:
            if self.shouldStop():
                return
            Stoppable.Stoppable.stop(self)

        logging.debug('CumulusService teardown: starting')
        try:
            #self.datasetLoadService.stopService()

            if self.cumulusActiveMachines.isConnected:
                self.cumulusActiveMachines.dropListener(self)
            self.cumulusActiveMachines.stopService()
            logging.debug('beginning teardown of channel factory')
            self._channelListener.stop()
            self._channelListener = None
            self.cumulusChannelFactoryThread.join()

            for reconnectThread in self.reconnectPersistentCacheIndexViewThreads:
                reconnectThread.join()

            logging.debug('tore down channel factory')

            #required to make the VDM get deallocated
            self.cumulusActiveMachines = None
            self.vdm = None
            self.offlineCache = None
            self.cumulusWorker = None

            self.deleteCumulusDiskCacheIfNecessary()


        except:
            logging.warn('error tearing down %s', ''.join(traceback.format_exc()))
            raise

    def deleteCumulusDiskCacheIfNecessary(self):
        if not os.path.exists(self.cumulusDiskCacheStorageDir):
            return
        try:
            shutil.rmtree(self.cumulusDiskCacheStorageDir)
        except:
            logging.warn(
                "Failed to delete the disk cache at %s:\n%s",
                self.cumulusDiskCacheStorageDir,
                traceback.format_exc()
                )

    def startThreads(self):
        """start all background thread processes"""
        assert not self.threadsStarted_
        self.threadsStarted_ = True
        self.cumulusActiveMachines.addListener(self)
        self.cumulusActiveMachines.startService()


    def onChannelConnect(self, portIndex, cumulusChannel):
        logging.debug("Received incoming connection on port id %d", portIndex)
        with self.lock:
            if self.shouldStop():
                logging.info("Rejecting a connection because we are no longer active")
                self._channelListener.rejectIncomingChannel(cumulusChannel)
                return

        # We process the incoming channel in a separate thread to minimize the
        # amount of processing done in the socket-accept thread.
        ManagedThread.ManagedThread(
            target=self.doChannelHandshake, args=(cumulusChannel,)
            ).start()

    def doChannelHandshake(self, channel):
        try:
            logging.debug("Worker %s beginning channel handshake", self.machineId)
            version = channel.getTimeout(HANDSHAKE_TIMEOUT)
            if version is None:
                logging.error(
                    "CAN'T ACCEPT CONNECTION!\n"
                    "CumulusService %s couldn't read client version within the configured timeout",
                    self.machineId
                    )

            if version != ufora.version:
                self.logBadUforaVersionOnChannel(version)
                channel.disconnect()
                return

            logging.debug(
                "CumulusService %s accepted connection from client with version %s",
                self.machineId,
                version
                )

            msgThatShouldBeMyOwnHash = channel.getTimeout(HANDSHAKE_TIMEOUT)
            if not self.isOwnHashInHandshakeMessage(msgThatShouldBeMyOwnHash):
                channel.disconnect()
                return

            msg = channel.getTimeout(HANDSHAKE_TIMEOUT)
            if msg is None:
                logging.error(
                    "CAN'T ACCEPT CONNECTION!\n"
                    "Worker %s didn't received remote machine ID during handshake",
                    self.machineId
                    )
                channel.disconnect()
                return

            clientOrMachine = CumulusNative.CumulusClientOrMachine.Machine(
                CumulusNative.MachineId(
                    Hash.Hash(0)
                    )
                )
            clientOrMachine.__setstate__(msg)

            hashGuid = Hash.Hash(0)
            msg = channel.getTimeout(HANDSHAKE_TIMEOUT)
            if msg is None:
                logging.error(
                    "CAN'T ACCEPT CONNECTION!\n"
                    "Worker %s didn't received handshake GUID",
                    self.machineId
                    )
                channel.disconnect()
                return

            hashGuid.__setstate__(msg)
            logging.debug(
                "Worker %s accepted connection with guid %s from %s",
                self.machineId,
                hashGuid,
                clientOrMachine
                )

            channel.write(
                ModuleImporter.builtinModuleImplVal().hash.__getstate__()
                )

            with self.lock:
                self._channelListener.setGroupIdForAcceptedChannel(
                    channel,
                    (clientOrMachine, hashGuid)
                    )

            logging.debug("CumulusService %s added a channel to group %s",
                          self.machineId,
                          (clientOrMachine, hashGuid))
        except:
            logging.error("FAILED TO PROCESS INCOMING CONNECTION: %s", traceback.format_exc())
            channel.disconnect()

    def logBadUforaVersionOnChannel(self, version):
        try:
            anId = CumulusNative.MachineId(Hash.Hash(0))
            anId.__setstate__(version)
            logging.error(
                "CumulusService %s received a bad version message that is, " \
                    "in fact, a machineId: %s",
                self.machineId,
                anId
                )
        except:
            logging.error(
                "CumulusService %s received a bad version message that is not a machineId: %s",
                self.machineId,
                repr(version)
                )

    def isOwnHashInHandshakeMessage(self, message):
        if message is None:
            logging.error("CAN'T ACCEPT CONNECTION!\n"
                          "Worker %s didn't receive an ID message during handshake.",
                          self.machineId)
            return False

        try:
            machineId = CumulusNative.MachineId(Hash.Hash(0))
            machineId.__setstate__(message)
        except:
            machineId = "not a valid machine ID"

        if isinstance(machineId, str) or machineId != self.machineId:
            logging.error(
                "CAN'T ACCESPT CONNECTION!\n"
                "Worker %s received connection intended for another machine (%s). %s != %s",
                self.machineId,
                machineId,
                repr(message),
                repr(self.machineId.__getstate__())
                )
            return False
        return True


    def onConnectionAvailable(self, channels, clientOrMachineAndGuid):
        def performConnect():
            clientOrMachine, guid = clientOrMachineAndGuid

            logging.info("Connection is available to %s with guid %s", clientOrMachine, guid)

            with self.lock:
                if self.shouldStop():
                    logging.info("Rejecting a connection because we are no longer active")
                    for channel in channels:
                        channel.disconnect()
                    return

            if clientOrMachine.isMachine():
                with self.lock:
                    if clientOrMachine.asMachine.machine in self.droppedMachineIds:
                        return
                    self.connectedMachines.add(clientOrMachine.asMachine.machine)

                    self.cumulusWorker.addMachine(
                        clientOrMachine.asMachine.machine,
                        channels,
                        ModuleImporter.builtinModuleImplVal(),
                        self.callbackScheduler
                        )
            else:
                self.cumulusWorker.addCumulusClient(
                    clientOrMachine.asClient.client,
                    channels,
                    ModuleImporter.builtinModuleImplVal(),
                    self.callbackScheduler
                    )

        ManagedThread.ManagedThread(
            target=performConnect, args=()
            ).start()


    def startService(self, onErrorCallback):
        if onErrorCallback is not None:
            logging.info("CumulusService handed a non-empty onErrorCallback which it will never use.")

        logging.debug(
            "Starting %s and waiting for it to be ready",
            self._channelListener
            )

        self._channelListener.registerConnectCallbackForAllPorts(self.onChannelConnect)
        self._channelListener.registerConnectionCompleteCallback(self.onConnectionAvailable)
        self.cumulusChannelFactoryThread.start()
        self._channelListener.blockUntilReady()

        logging.debug("Registering machineId %s in CumulusActiveMachines", str(self.machineId.guid))

        self.cumulusActiveMachines.registerSelfAsActive(
            self.ownAddress,
            [listener.port for listener in self._channelListener.listeners],
            str(self.machineId.guid)
            )

        logging.debug("CumulusService: starting threads")
        self.startThreads()

    def updatePersistentCacheView(self):
        while not self.shouldStop():
            try:
                self.persistentCacheIndex.resetView(
                    self.viewFactory.createView(retrySeconds=10.0, numRetries=10)
                    )

                #if we're here, we're successful
                return
            except:
                logging.info("Cumulus failed to reconnect views for PersistentCacheIndex: %s",
                    traceback.format_exc()
                    )
                #try again
                time.sleep(1.0)

    def onReconnectedToSharedState(self):
        thread = ManagedThread.ManagedThread(
            target=self.updatePersistentCacheView, args=()
            )

        self.reconnectPersistentCacheIndexViewThreads.append(thread)

        thread.start()

    def onWorkerDrop(self, machineIdAsString):
        machineId = CumulusNative.MachineId(Hash.Hash.stringToHash(machineIdAsString))

        if machineId == self.machineId:
            return

        logging.info("CumulusService %s dropped worker %s", self.machineId, machineId)

        try:
            hadMachine = False
            with self.lock:
                if machineId in self.connectedMachines:
                    hadMachine = True
                self.connectingMachines.discard(machineId)
                self.connectedMachines.discard(machineId)
                self.droppedMachineIds.add(machineId)

            if hadMachine:
                self.cumulusWorker.dropMachine(machineId)
        except:
            logging.error("Failed to drop worker: %s", traceback.format_exc())
            raise

    def onWorkerAdd(self, ip, ports, machineIdAsString):
        machineId = CumulusNative.MachineId(Hash.Hash.stringToHash(machineIdAsString))

        if machineId <= self.machineId:
            logging.info("Worker %s detected worker %s, and waiting for incoming connection",
                         self.machineId,
                         machineId)

            #only connect one way. If the worker is larger than us, then we connect to it
            return

        guid = Hash.Hash.sha1(str(uuid.uuid4()))

        logging.info(
            "Worker %s detected worker %s and initiating connection with guid %s",
            self.machineId,
            machineId,
            guid
            )

        with self.lock:
            # Track that we are trying to connect to this machine
            self.connectingMachines.add(machineId)

        ManagedThread.ManagedThread(
            target=self.onWorkerAdd2, args=(machineId, ip, ports, guid)
            ).start()

    def onWorkerAdd2(self, machineId, ip, ports, guid):
        logging.debug(
            "CumulusService %s adding worker %s and connecting to it with guid %s",
            self.machineId,
            machineId,
            guid
            )

        assert len(ports) == 2
        channels = []
        while self.shouldConnectToMachine(machineId):
            try:
                for channel in channels:
                    channel.disconnect()
                channels = []

                for port in ports:
                    channel = None
                    tries = 0

                    while channel is None and tries < 3:
                        channel = self.connectToRemoteWorker(machineId, ip, port, guid)
                        tries += 1

                    if channel is None:
                        logging.error(
                            "Unable to connect to worker %s on %s:%s with guid %s.",
                            machineId,
                            ip,
                            port,
                            guid
                            )
                        continue

                    channels.append(channel)

                with self.lock:
                    if machineId in self.droppedMachineIds:
                        logging.warn("not accepting %s", machineId)
                    self.connectedMachines.add(machineId)
                    self.connectingMachines.discard(machineId)

                    self.cumulusWorker.addMachine(
                        machineId,
                        channels,
                        ModuleImporter.builtinModuleImplVal(),
                        self.callbackScheduler
                        )

                logging.info("Connection is available to Worker %s with guid %s",
                             machineId,
                             guid)
                return
            except:
                logging.error("Failed to add worker %s: %s", machineId, traceback.format_exc())

    def shouldConnectToMachine(self, machineId):
        with self.lock:
            return machineId in self.connectingMachines and not self.shouldStop()

    def connectToRemoteWorker(self, machineId, ip, port, guid):
        logging.debug("Attempting to connect to machine %s on %s:%s with guid %s",
                      machineId,
                      ip,
                      port,
                      guid)
        try:
            stringChannel = self._channelFactory.createChannel((ip, port))
        except:
            logging.error("CAN'T CONNECT TO WORKER ON %s:%s!\n"
                          "This may be a temporary failure but if the problem persists, "
                          "check the workers' network configuration and verify "
                          "that the machines can see each other.",
                          ip, port)
            raise

        stringChannel.write(ufora.version)

        stringChannel.write(machineId.__getstate__())

        #initiate the handshake
        stringChannel.write(
            CumulusNative.CumulusClientOrMachine.Machine(
                self.machineId
                ).__getstate__()
            )

        stringChannel.write(guid.__getstate__())

        logging.debug("CumulusService %s wrote handshake for %s with guid %s",
                      self.machineId,
                      machineId,
                      guid)

        channelAsQueue = stringChannel.makeQueuelike(self.callbackScheduler)

        msg = channelAsQueue.getTimeout(HANDSHAKE_TIMEOUT)

        if msg is None:
            logging.error("CAN'T CONNECT TO WORKER ON %s:%s!\n"
                          "While attempting to add worker %s with guid %s, "
                          "Worker %s did not receive a builtin hash message "
                          "during handshake.\n"
                          "Verify that the ufora worker is running on the remote machine.",
                          ip, port,
                          machineId, guid,
                          self.machineId)
            return None

        otherWorkersBuiltinHash = Hash.Hash(0)
        otherWorkersBuiltinHash.__setstate__(msg)

        builtinsAgree = otherWorkersBuiltinHash == ModuleImporter.builtinModuleImplVal().hash

        if not builtinsAgree:
            logging.critical("CAN'T CONNECT TO WORKER ON %s:%s!\n"
                             "Worker %s could not connect to Worker %s as they have "
                             "different builtins; former's builtin hash: %s, latter's builtin hash: "
                             "%s\n"
                             "Verify that both machines run the same ufora version.",
                             ip, port,
                             self.machineId,
                             machineId,
                             ModuleImporter.builtinModuleImplVal().hash,
                             otherWorkersBuiltinHash)

            channelAsQueue.disconnect()
            return None

        return channelAsQueue

