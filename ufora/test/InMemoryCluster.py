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
import time
import threading
import uuid

import ufora.config.Setup as Setup
import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines
import ufora.cumulus.distributed.CumulusGatewayRemote as CumulusGatewayRemote
import ufora.cumulus.distributed.CumulusService as CumulusService
import ufora.distributed.SharedState.Connections.InMemoryChannelFactory as InMemorySharedStateChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.networking.MultiChannelListener as MultiChannelListener
import ufora.native.StringChannel as StringChannelNative
import ufora.util.ManagedThread as ManagedThread
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.native.Cumulus as CumulusNative

DEFAULT_MAX_RAM_CACHE_SIZE = 125 * 1024 * 1024
DEFAULT_VECTOR_RAM_CACHE_SIZE = 100 * 1024 * 1024
DEFAULT_PER_MACHINE_THROUGHPUT = 200 * 1024 * 1024

DEFAULT_THREAD_COUNT = 2

class InMemoryChannelListener(object):
    def __init__(self, address, port, channelManager):
        self.address = address
        self.port = port
        self.channelManager = channelManager
        self.connectionCallback = None
        self.isStarted = threading.Event()

    def __str__(self):
        return "InMemoryChannelListener(%s, %d)" % (self.address, self.port)

    def start(self):
        logging.info("Registering channel listener on %s:%d", self.address, self.port)
        self.channelManager.registerChannelListener(self.address,
                                                    self.port,
                                                    self.onChannelConnected)
        self.isStarted.set()

    def stop(self):
        self.channelManager.unregisterChannelListener(self.address, self.port)

    def blockUntilReady(self):
        t0 = time.time()
        self.isStarted.wait()
        logging.info("Took %s to blockUntilReady", time.time() - t0)

    def registerConnectCallback(self, callback):
        self.connectionCallback = callback

    def onChannelConnected(self, channel):
        if self.connectionCallback is not None:
            self.connectionCallback(channel)


class InMemoryChannelManager(object):
    def __init__(self, callbackScheduler, throughput):
        self.lock = threading.Lock()
        self.listeners = {}
        self.rateLimitedChannelGroupsForEachListener = {}

        self.callbackScheduler = callbackScheduler
        self.perMachineThroughput = throughput

    def registerChannelListener(self, address, port, connectionCallback):
        with self.lock:
            assert (address, port) not in self.listeners

            key = (str(address), int(port))

            self.listeners[key] = connectionCallback
            self.rateLimitedChannelGroupsForEachListener[key] = (
                StringChannelNative.createRateLimitedStringChannelGroup(
                    self.callbackScheduler,
                    self.perMachineThroughput
                    )
                )

    def unregisterChannelListener(self, address, port):
        with self.lock:
            if (address, port) in self.listeners:
                del self.listeners[(address, port)]
                del self.rateLimitedChannelGroupsForEachListener[(address, port)]

    def createChannelFactory(self):
        return RateLimitedInMemoryCumulusChannelFactory(self)

    def createChannelToEndpoint(self, ipEndpoint):
        with self.lock:
            assert len(ipEndpoint) == 2

            # we expect addresses to be strings and ports to be ints
            ipEndpoint = (str(ipEndpoint[0]), int(ipEndpoint[1]))

            assert ipEndpoint in self.listeners, (
                "No listeners registered on endpoint: %s. Registered listeners: %s" %
                    (ipEndpoint, self.listeners)
                )

            clientChannel, serverChannel = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)

            rateLimitedServerChannel = (
                self.rateLimitedChannelGroupsForEachListener[ipEndpoint].wrap(
                    serverChannel
                    )
                )

            self.listeners[ipEndpoint](rateLimitedServerChannel.makeQueuelike(self.callbackScheduler))

            return clientChannel

class RateLimitedInMemoryCumulusChannelFactory(object):
    def __init__(self, channelManager):
        self.channelManager = channelManager
        self.rateLimitedChannelGroup = (
            StringChannelNative.createRateLimitedStringChannelGroup(
                self.channelManager.callbackScheduler,
                self.channelManager.perMachineThroughput
                )
            )

    def createChannel(self, ipEndpoint):
        return self.rateLimitedChannelGroup.wrap(
            self.channelManager.createChannelToEndpoint(ipEndpoint)
            )



IN_MEMORY_CLUSTER_SS_PING_INTERVAL = 10.0


class InMemoryClient(object):
    def __init__(self, simulation):
        self.clusterName = 'test'
        self.simulation = simulation
        self.ownAddress = str(uuid.uuid4())
        self.desire = {}

    def getClusterName(self):
        return self.clusterName

    def getAssignedMachineName(self):
        return 'machine@%s' % self.ownAddress

    def getWorkerStatusCounts(self):
        return self.desire, self.desire

    def getOwnAddressInternal(self):
        return self.ownAddress

    def desireNumberOfWorkers(self, numWorkers, blocking = False, timeout = 10.0):
        self.simulation.desireNumCumuli(numWorkers, blocking, timeout)
        self.desire[('ec2', 'm1.large', 2)] = (numWorkers, 3600)

        logging.info("DESIRING WORKERS %s", numWorkers)

    def desireNumberOfWorkersByType(self, typeDict, blocking = False, timeout = 10.0):
        self.simulation.desireNumCumuli(sum(typeDict.values()), blocking, timeout)
        self.desire = typeDict

        logging.info("InMemoryClient added workers: %s", typeDict)


class InMemoryClusterManagerConnection(object):
    '''
    Used by Mediator to talk to the inMemory cluster
    '''
    def __init__(self, inMemoryCluster):
        self.inMemoryCluster = inMemoryCluster
        self._onClusterResponse = None
        self.desires = {}

        self.callbackQueue = Queue.Queue()
        self.callbackThread = ManagedThread.ManagedThread(target=self.callbackLoop)

    def registerOnClusterResponseCallback(self, callback):
        self._onClusterResponse = callback

    def callbackLoop(self):
        callback = self.callbackQueue.get()
        while callback is not None:
            callback()
            time.sleep(.01)
            callback = self.callbackQueue.get()

    def startService(self):
        self.callbackThread.start()

    def stopService(self):
        self.callbackQueue.put(None)
        self.callbackThread.join()

    def publishDesireToClusterManager(self, user, desire):
        self.desires[user] = desire
        machineSum = 0
        for user in self.desires:
            machineSum += sum(d[0] for d in self.desires[user].itervalues())
        self.inMemoryCluster.desireNumCumuli(machineSum)


class InMemoryCluster(object):
    def __init__(self,
            cumulusVectorRamCacheSizeOverride = DEFAULT_VECTOR_RAM_CACHE_SIZE,
            cumulusMaxRamCacheSizeOverride = DEFAULT_MAX_RAM_CACHE_SIZE,
            cumulusThreadCountOverride = DEFAULT_THREAD_COUNT,
            remoteGatewayRamCacheSizeOverride = DEFAULT_MAX_RAM_CACHE_SIZE,
            perMachineThroughput = DEFAULT_PER_MACHINE_THROUGHPUT
            ):
        self.cumulusMaxRamCacheSizeOverride = cumulusMaxRamCacheSizeOverride
        self.cumulusVectorRamCacheSizeOverride = cumulusVectorRamCacheSizeOverride

        self.callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
        self.callbackScheduler = self.callbackSchedulerFactory.createScheduler("InMemoryCluster", 1)

        self.cumulusThreadCountOverride = cumulusThreadCountOverride
        self.remoteGatewayCacheSize = remoteGatewayRamCacheSizeOverride

        self.sharedStateManager = SharedStateService.KeyspaceManager(
            10001,
            1,
            cachePathOverride="",
            pingInterval = IN_MEMORY_CLUSTER_SS_PING_INTERVAL,
            maxOpenFiles=100
            )

        self.sharedStateChannelFactory = (
            InMemorySharedStateChannelFactory.InMemoryChannelFactory(
                self.callbackScheduler,
                self.sharedStateManager
                )
            )

        self.sharedStateViewFactory = ViewFactory.ViewFactory(self.sharedStateChannelFactory)

        self.client = InMemoryClient(self)
        self.cumuli = []
        self.nextCumulusAddress = 0

        self.channelManager = InMemoryChannelManager(self.callbackScheduler, perMachineThroughput)

        self.inMemoryDemuxingChannel = \
            InMemorySharedStateChannelFactory.SerializedToManagerChannelFactory(
                self.callbackScheduler,
                self.sharedStateManager,
                "SharedState"
                )

    def disconnectAllWorkersFromSharedState(self):
        self.sharedStateChannelFactory.disconnectAllChannels()

    def createMultiChannelListener(self, callbackScheduler, ports, address):
        def makeChannelListener(cbScheduler, port, portScanIncrement=0):
            return self.createChannelListener(cbScheduler, address, port)

        return MultiChannelListener.MultiChannelListener(callbackScheduler,
                                                         ports,
                                                         makeChannelListener)



    def createChannelListener(self, callbackScheduler, address, port):
        return InMemoryChannelListener(address, port, self.channelManager)

    #def getDesirePublisher(self, user):
        #with self.sharedStateViewFactory:
            #desirePublisher = SynchronousDesirePublisher.SynchronousDesirePublisher(user)
            #desirePublisher.startService()
            #return desirePublisher


    def createCumulusGateway(self, callbackScheduler, vdm=None):
        logging.info("InMemoryCluster creating a RemoteGateway")
        return CumulusGatewayRemote.RemoteGateway(
            self.callbackScheduler,
            VectorDataManager.constructVDM(
                self.callbackScheduler,
                self.remoteGatewayCacheSize
                ),
            self.channelManager.createChannelFactory(),
            CumulusActiveMachines.CumulusActiveMachines(
                self.client.getClusterName(),
                self.sharedStateViewFactory
                ),
            self.client.getClusterName(),
            self.sharedStateViewFactory
            )

    def start(self):
        pass

    def stop(self):
        for service in self.cumuli:
            logging.info("stopping in-memory cumulus: %s", service)
            service.stopService()

    def teardown(self):
        self.client = None
        self.cumuli = None
        self.channelManager = None
        self.sharedStateManager = None

        import gc
        gc.collect()

    def createServiceAndServiceThread(self):
        config = Setup.config()
        config.cumulusMaxRamCacheMB = self.cumulusMaxRamCacheSizeOverride
        config.cumulusVectorRamCacheMB = self.cumulusVectorRamCacheSizeOverride
        config.cumulusServiceThreadCount = self.cumulusThreadCountOverride
        config.cumulusDiskCacheStorageSubdirectory = str(uuid.uuid4())

        ownAddress = str(uuid.uuid4())
        callbackScheduler = self.callbackSchedulerFactory.createScheduler(
            "InMemoryClusterChild",
            1)
        channelListener = self.createMultiChannelListener(
            callbackScheduler,
            [Setup.config().cumulusControlPort, Setup.config().cumulusDataPort],
            ownAddress)
        service = CumulusService.CumulusService(
            clusterName='test',
            ownAddress=ownAddress,
            channelListener=channelListener,
            channelFactory=self.channelManager.createChannelFactory(),
            eventHandler=CumulusNative.CumulusWorkerHoldEventsInMemoryEventHandler(),
            callbackScheduler=callbackScheduler,
            diagnosticsDir=None,
            config=config,
            viewFactory=self.sharedStateViewFactory
            )
        service.startService(lambda: None)
        return service

    def desireNumCumuli(self, numNodes, blocking=False, timeout=20.0):
        maxTime = time.time() + timeout

        if numNodes > len(self.cumuli):
            newCumuli = []
            while numNodes > len(self.cumuli):
                cumulus = self.createServiceAndServiceThread()
                logging.info("InMemory cluster started a cumulus node: %s, %s", cumulus, cumulus.machineId)
                self.cumuli.append(cumulus)
                newCumuli.append(cumulus)

            if blocking:
                for cumulus in newCumuli:
                    # Wait up to timeout seconds for the other cumuli to discover the new machine
                    success = False
                    while time.time() < maxTime:
                        missing = False
                        for c in self.cumuli:
                            if cumulus == c:
                                continue
                            if cumulus.machineId not in c.connectedMachines:
                                logging.info("Machine %s not connected to %s", cumulus.machineId, c.machineId)
                                missing = True
                        if not missing:
                            success = True
                            break
                        else:
                            time.sleep(0.1)

                    assert success

        if numNodes < len(self.cumuli):
            stoppedCumuli = []
            while numNodes < len(self.cumuli):
                cumulus = self.cumuli.pop()
                cumulus.stopService()
                stoppedCumuli.append(cumulus)

            if blocking:
                for cumulus in stoppedCumuli:
                    # Wait up to timeout seconds for the other cumuli to discover the dropped machine
                    success = False
                    while time.time() < maxTime:
                        present = False
                        for c in self.cumuli:
                            if cumulus == c:
                                continue
                            if cumulus.machineId in c.connectedMachines:
                                present = True
                        if not present:
                            success = True
                            break
                        else:
                            time.sleep(0.1)

                    assert success

                logging.info("InMemory cluster killed a cumulus node: %s, %s", cumulus, cumulus.machineId)

        assert len(self.cumuli) == numNodes


