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

import os
import cPickle as pickle
import time
import random
import logging
import traceback
import sys
import tempfile
import shutil
import uuid
import ufora.native.FORA as ForaNative
import ufora.native.Hash as HashNative
import ufora.native.Cumulus as CumulusNative
import ufora.native.StringChannel as StringChannelNative
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.FORA.python.FORA as FORA
import ufora.config.Setup as Setup


import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.SharedState.Connections.InMemoryChannelFactory as InMemorySharedStateChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.cumulus.distributed.PythonIoTaskService as PythonIoTaskService
import ufora.distributed.Storage.S3ObjectStore as S3ObjectStore


IN_MEMORY_CLUSTER_SS_PING_INTERVAL = 10.0

def machineId(ix, seed = None):
    h = HashNative.Hash(ix)
    if seed is not None:
        h = h + HashNative.Hash.sha1(seed)

    return CumulusNative.MachineId(h)

def clientId(ix):
    return CumulusNative.CumulusClientId(HashNative.Hash(ix))

def createInMemorySharedStateViewFactory(callbackSchedulerToUse = None):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    sharedStateManager = SharedStateService.KeyspaceManager(
        10001,
        1,
        cachePathOverride="",
        pingInterval = IN_MEMORY_CLUSTER_SS_PING_INTERVAL,
        maxOpenFiles=100
        )

    sharedStateChannelFactory = (
        InMemorySharedStateChannelFactory.InMemoryChannelFactory(
            callbackSchedulerToUse.getFactory().createScheduler("SharedState", 1),
            sharedStateManager
            )
        )

    return ViewFactory.ViewFactory(sharedStateChannelFactory)

def createWorker_(machineId,
                  viewFactory,
                  callbackSchedulerToUse,
                  threadCount,
                  memoryLimitMb,
                  cacheFunction,
                  pageSizeOverride,
                  disableEventHandler):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    vdm = ForaNative.VectorDataManager(
        callbackSchedulerToUse,
        pageSizeOverride if pageSizeOverride is not None else
        1 * 1024 * 1024 if memoryLimitMb < 1000 else
        5 * 1024 * 1024 if memoryLimitMb < 5000 else
        50 * 1024 * 1024
        )

    vdm.setMemoryLimit(
        int(memoryLimitMb * 1024 * 1024),
        min(int(memoryLimitMb * 1.25 * 1024 * 1024),
            int((memoryLimitMb + 1024 * 2) * 1024 * 1024))
        )

    vdm.setPersistentCacheIndex(
        CumulusNative.PersistentCacheIndex(
            "test",
            viewFactory.createView(),
            callbackSchedulerToUse
            )
        )

    cache = cacheFunction()

    if disableEventHandler:
        eventHandler = CumulusNative.CumulusWorkerIgnoreEventHandler()
    else:
        eventHandler = CumulusNative.CumulusWorkerHoldEventsInMemoryEventHandler()

    return (
        CumulusNative.CumulusWorker(
            callbackSchedulerToUse,
            CumulusNative.CumulusWorkerConfiguration(
                machineId,
                threadCount,
                CumulusNative.CumulusCheckpointPolicy.None(),
                ExecutionContext.createContextConfiguration(),
                ""
                ),
            vdm,
            cache,
            eventHandler
            ),
        vdm,
        eventHandler
        )

def createClient_(clientId, callbackSchedulerToUse = None):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    vdm = ForaNative.VectorDataManager(callbackSchedulerToUse, 5 * 1024 * 1024)
    vdm.setMemoryLimit(100 * 1024 * 1024, 125 * 1024 * 1024)

    return (
        CumulusNative.CumulusClient(vdm, clientId, callbackSchedulerToUse),
        vdm
        )

def createComputationDefinition(*args):
    return CumulusNative.ComputationDefinition.Root(
                CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(
                    [CumulusNative.ComputationDefinitionTerm.Value(ForaNative.ImplValContainer(x), None)
                        if not isinstance(x, CumulusNative.ComputationDefinition) else
                            CumulusNative.ComputationDefinitionTerm.Subcomputation(x.asRoot.terms)
                        for x in args]
                    )
                )

def computeUsingSeveralWorkers(
            expressionText,
            s3Service,
            count,
            objectStore=None,
            wantsStats = False,
            timeout=10,
            memoryLimitMb = 100,
            blockUntilConnected = False,
            sharedStateViewFactory = None,
            threadCount = 2,
            ioTaskThreadOverride = None,
            returnSimulation = False,
            useInMemoryCache = True,
            channelThroughputMBPerSecond = None,
            pageSizeOverride = None,
            disableEventHandler = False
            ):
    simulation = InMemoryCumulusSimulation(
            workerCount=count,
            clientCount=1,
            s3Service=s3Service,
            objectStore=objectStore,
            memoryPerWorkerMB=memoryLimitMb,
            threadsPerWorker=threadCount,
            callbackScheduler=None,
            sharedStateViewFactory=sharedStateViewFactory,
            ioTaskThreadOverride=ioTaskThreadOverride,
            useInMemoryCache=useInMemoryCache,
            channelThroughputMBPerSecond=channelThroughputMBPerSecond,
            pageSizeOverride=pageSizeOverride,
            disableEventHandler=disableEventHandler
            )

    if returnSimulation:
        try:
            result = simulation.compute(expressionText, timeout=timeout, wantsStats=wantsStats)
            return result, simulation
        except Exception as e:
            logging.error("Simulation threw an exception: %s", traceback.format_exc())
            raise e
    else:
        try:
            return simulation.compute(expressionText, timeout=timeout, wantsStats=wantsStats)
        except Exception as e:
            logging.error("Simulation threw an exception: %s", traceback.format_exc())
            e = None
            return None
        finally:
            simulation.teardown()

class InMemoryCumulusSimulation(object):
    def __init__(self,
                workerCount,
                clientCount,
                memoryPerWorkerMB,
                threadsPerWorker,
                s3Service,
                objectStore=None,
                callbackScheduler=None,
                sharedStateViewFactory=None,
                ioTaskThreadOverride=None,
                useInMemoryCache=True,
                channelThroughputMBPerSecond=None,
                pageSizeOverride=None,
                disableEventHandler=False,
                machineIdHashSeed=None
                ):
        self.useInMemoryCache = useInMemoryCache
        self.machineIdHashSeed = machineIdHashSeed

        if not self.useInMemoryCache:
            self.diskCacheCount = 0
            if os.getenv("CUMULUS_DATA_DIR") is None:
                self.diskCacheStorageDir = tempfile.mkdtemp()
            else:
                self.diskCacheStorageDir = os.path.join(
                    os.getenv("CUMULUS_DATA_DIR"),
                    str(uuid.uuid4())
                    )
        self.ioTaskThreadOverride = ioTaskThreadOverride
        self.workerCount = 0
        self.disableEventHandler = disableEventHandler
        self.clientCount = 0
        self.memoryPerWorkerMB = memoryPerWorkerMB
        self.threadsPerWorker = threadsPerWorker
        self.s3Service = s3Service
        self.objectStore = objectStore
        if self.objectStore is None:
            s3 = s3Service()
            if isinstance(s3, InMemoryS3Interface.InMemoryS3Interface):
                objectStoreBucket = "object_store_bucket"
                s3.setKeyValue(objectStoreBucket, 'dummyKey', 'dummyValue')
                s3.deleteKey(objectStoreBucket, 'dummyKey')
            else:
                objectStoreBucket = Setup.config().userDataS3Bucket
            self.objectStore = S3ObjectStore.S3ObjectStore(
                s3Service,
                objectStoreBucket,
                prefix="test/")
        self.callbackScheduler = callbackScheduler or CallbackScheduler.singletonForTesting()
        self.sharedStateViewFactory = (
            sharedStateViewFactory or createInMemorySharedStateViewFactory(self.callbackScheduler)
            )
        self.channelThroughputMBPerSecond = channelThroughputMBPerSecond
        self.resultVDM = ForaNative.VectorDataManager(self.callbackScheduler, 5 * 1024 * 1024)
        self.pageSizeOverride = pageSizeOverride

        self.rateLimitedChannelGroupsForEachListener = []
        self.workersVdmsAndEventHandlers = []
        self.machineIds = []
        self.machineIdsEverAllocated = 0
        self.clientsAndVdms = []
        self.loadingServices = []
        self.clientTeardownGates = []
        self.workerTeardownGates = []


        for ix in range(workerCount):
            self.addWorker()
        for ix in range(clientCount):
            self.addClient()

        if clientCount:
            self.listener = self.getClient(0).createListener()
        else:
            self.listener = None

    def allocateMachineId(self):
        self.machineIdsEverAllocated += 1
        return machineId(self.machineIdsEverAllocated - 1, self.machineIdHashSeed)


    def addWorker(self):
        self.workerCount += 1

        newMachineId = self.allocateMachineId()

        self.machineIds.append(newMachineId)

        self.workersVdmsAndEventHandlers.append(
            createWorker_(
                newMachineId,
                self.sharedStateViewFactory,
                memoryLimitMb = self.memoryPerWorkerMB,
                threadCount=self.threadsPerWorker,
                callbackSchedulerToUse = self.callbackScheduler,
                cacheFunction = self.cacheFunction,
                pageSizeOverride = self.pageSizeOverride,
                disableEventHandler = self.disableEventHandler
                )
            )

        if self.channelThroughputMBPerSecond is not None:
            self.rateLimitedChannelGroupsForEachListener.append(
                StringChannelNative.createRateLimitedStringChannelGroup(
                    self.callbackScheduler,
                    int(self.channelThroughputMBPerSecond * 1024 * 1024 * (.5 + random.random()))
                    )
                )

        self.workersVdmsAndEventHandlers[-1][0].startComputations()

        for ix1 in range(len(self.workersVdmsAndEventHandlers)-1):
            ix2 = len(self.workersVdmsAndEventHandlers)-1
            self.wireWorkersTogether_(ix1, ix2)

        for ix1 in range(len(self.clientsAndVdms)):
            ix2 = len(self.workersVdmsAndEventHandlers)-1
            self.wireWorkerToClient_(ix2, ix1)

        s3InterfaceFactory = self.s3Service.withMachine(self.machineIdsEverAllocated - 1)

        worker, workerVdm, _ = self.workersVdmsAndEventHandlers[-1]

        loadingService = PythonIoTaskService.PythonIoTaskService(
            s3InterfaceFactory,
            self.objectStore,
            workerVdm,
            worker.getExternalDatasetRequestChannel(self.callbackScheduler)
                .makeQueuelike(self.callbackScheduler),
            threadCount=self.ioTaskThreadOverride,
            maxObjectStoreAttempts=1,
            objectStoreFailureInterval=0
            )

        loadingService.startService()

        self.loadingServices.append(loadingService)

        self.workerTeardownGates.append(workerVdm.getVdmmTeardownGate())

    def wireWorkersTogether_(self, ix1, ix2):
        worker1Channel1, worker2Channel1 = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)
        worker1Channel2, worker2Channel2 = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)

        if self.channelThroughputMBPerSecond is not None:
            worker1Channel1 = self.rateLimitedChannelGroupsForEachListener[ix1].wrap(worker1Channel1)
            worker1Channel2 = self.rateLimitedChannelGroupsForEachListener[ix1].wrap(worker1Channel2)

            worker2Channel1 = self.rateLimitedChannelGroupsForEachListener[ix2].wrap(worker2Channel1)
            worker2Channel2 = self.rateLimitedChannelGroupsForEachListener[ix2].wrap(worker2Channel2)

        self.workersVdmsAndEventHandlers[ix1][0].addMachine(self.machineIds[ix2], [worker1Channel1, worker1Channel2], ForaNative.ImplValContainer(), self.callbackScheduler)
        self.workersVdmsAndEventHandlers[ix2][0].addMachine(self.machineIds[ix1], [worker2Channel1, worker2Channel2], ForaNative.ImplValContainer(), self.callbackScheduler)

    def addClient(self):
        self.clientCount += 1

        self.clientsAndVdms.append(
            createClient_(
                clientId(len(self.clientsAndVdms)),
                callbackSchedulerToUse = self.callbackScheduler
                )
            )

        for ix1 in range(len(self.workersVdmsAndEventHandlers)):
            ix2 = len(self.clientsAndVdms)-1
            self.wireWorkerToClient_(ix1, ix2)

        self.clientTeardownGates.append(self.clientsAndVdms[-1][1].getVdmmTeardownGate())


    def wireWorkerToClient_(self, ix1, ix2):
        workerChannel1, clientChannel1 = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)
        workerChannel2, clientChannel2 = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)
        self.workersVdmsAndEventHandlers[ix1][0].addCumulusClient(clientId(ix2), [workerChannel1, workerChannel2], ForaNative.ImplValContainer(), self.callbackScheduler)
        self.clientsAndVdms[ix2][0].addMachine(self.machineIds[ix1], [clientChannel1, clientChannel2], ForaNative.ImplValContainer(), self.callbackScheduler)


    def cacheFunction(self):
        if self.useInMemoryCache:
            return CumulusNative.SimpleOfflineCache(self.callbackScheduler, 1000 * 1024 * 1024)
        else:
            self.diskCacheCount += 1
            return CumulusNative.DiskOfflineCache(
                    self.callbackScheduler,
                    os.path.join(self.diskCacheStorageDir, str(self.diskCacheCount)),
                    100 * 1024 * 1024 * 1024,
                    100000
                    )

    def stopServices(self):
        for service in self.loadingServices:
            service.teardown()

        for worker,vdm,eventHandler in self.workersVdmsAndEventHandlers:
            worker.teardown()

    def dropTopWorker(self):
        assert self.workerCount >= 1
        self.dropWorkerByIndex(self.workerCount-1)

    def dropBottomWorker(self):
        assert self.workerCount >= 1
        self.dropWorkerByIndex(0)

    def dropWorkerByIndex(self, index):
        assert self.workerCount >= 1

        for ix in range(self.workerCount):
            if ix != index:
                self.getWorker(ix).dropMachine(self.machineIds[index])

        for ix in range(self.clientCount):
            self.getClient(ix).dropMachine(self.machineIds[index])

        worker = self.getWorker(index)
        worker.teardown()
        worker = None

        teardownGate = self.workerTeardownGates[index]
        self.loadingServices[index].teardown()

        if self.channelThroughputMBPerSecond:
            self.rateLimitedChannelGroupsForEachListener.pop(index)

        self.machineIds.pop(index)

        self.workerTeardownGates.pop(index)

        self.loadingServices.pop(index)

        self.workersVdmsAndEventHandlers.pop(index)

        self.workerCount -= 1

        if not teardownGate.wait(30):
            raise UserWarning("Failed to tear down a cumulus")


    def teardown(self):
        if self.loadingServices is None:
            logging.error("Tried to tear down an InMemoryCumulusSimulation twice")
            return

        self.stopServices()

        self.workersVdmsAndEventHandlers = None
        self.clientsAndVdms = None
        self.loadingServices = None
        self.listener = None

        for gate in self.workerTeardownGates + self.clientTeardownGates:
            if not gate.wait(30):
                import ufora.util.StackTraceLoop as StackTraceLoop
                StackTraceLoop.writeStackTraceSummary(sys.stderr)

                import ufora.native.Tests as TestsNative
                TestsNative.forceStackdump()
                raise UserWarning("Failed to tear down a simulation")

        if not self.useInMemoryCache:
            shutil.rmtree(self.diskCacheStorageDir)

    def getClient(self, clientIndex):
        return self.clientsAndVdms[clientIndex][0]

    def getClientVdm(self, clientIndex):
        return self.clientsAndVdms[clientIndex][1]

    def getWorker(self, workerIndex):
        return self.workersVdmsAndEventHandlers[workerIndex][0]

    def getGlobalScheduler(self):
        for worker, _, _ in self.workersVdmsAndEventHandlers:
            s = worker.getGlobalScheduler()
            if s is not None:
                return s

    def getWorkerVdm(self, workerIndex):
        return self.workersVdmsAndEventHandlers[workerIndex][1]

    def getWorkerCount(self):
        return len(self.workersVdmsAndEventHandlers)

    def blockUntilWorkersAreConnected(self, timeout):
        for worker, _, _ in self.workersVdmsAndEventHandlers:
            self.blockUntilWorkerIsConnected_(worker, timeout)

    def triggerCheckpointGarbageCollection(self, completePurge):
        self.getClient(0).triggerCheckpointGarbageCollection(completePurge)

    def getCurrentCheckpointStatistics(self, timeout):
        h = self.getClient(0).requestCheckpointStatus()

        t0 = time.time()
        while True:
            t1 = time.time()

            if t1 - t0 > timeout:
                return None

            msg = self.listener.getTimeout(timeout - (t1 - t0))

            if msg is not None and isinstance(msg, tuple) and msg[0] == h:
                return msg[1]


    def blockUntilWorkerIsConnected_(self, worker, timeout):
        t0 = time.time()

        while not worker.hasEstablishedHandshakeWithExistingMachines():
            time.sleep(0.01)

            if time.time() - t0 > timeout:
                raise UserWarning("Failed to connect to worker in %s seconds" % timeout)

    def executeExternalIoTask(self, externalIoTask, timeout = 10.0, wantsStats = False):
        t0 = time.time()
        guid = self.getClient(0).createExternalIoTask(externalIoTask)

        while True:
            t1 = time.time()

            if t1 - t0 > timeout:
                self.dumpSchedulerEventStreams()
                raise UserWarning("Timed out after %s seconds" % (t1 - t0))

            msg = self.listener.getTimeout(timeout - (t1 - t0))

            if msg is not None:
                if (isinstance(msg, CumulusNative.ExternalIoTaskCompleted)
                            and msg.taskId == guid):
                    return msg.result

    def waitForResult(self, computationId, timeout = 10.0, wantsStats = False):
        t0 = time.time()
        while True:
            t1 = time.time()

            if t1 - t0 > timeout:
                self.dumpSchedulerEventStreams()
                raise UserWarning("Timed out after %s seconds" % (t1 - t0))

            msg = self.listener.getTimeout(timeout - (t1 - t0))

            if msg is not None:
                if (isinstance(msg, CumulusNative.ComputationResult)
                            and msg.computation == computationId):
                    if wantsStats:
                        return msg.deserializedResult(self.resultVDM), msg.statistics
                    else:
                        return msg.deserializedResult(self.resultVDM)

    def waitForAnyResult(self, timeout = 10.0, wantsStats = False):
        t0 = time.time()
        while True:
            t1 = time.time()

            if t1 - t0 > timeout:
                self.dumpSchedulerEventStreams()
                raise UserWarning("Timed out after %s seconds" % (t1 - t0))

            msg = self.listener.getTimeout(timeout - (t1 - t0))

            if msg is not None:
                if isinstance(msg, CumulusNative.ComputationResult):
                    if wantsStats:
                        return msg.deserializedResult(self.resultVDM), msg.statistics
                    else:
                        return msg.deserializedResult(self.resultVDM)

    def getAnyResult(self):
        while True:
            msg = self.listener.getNonblock()

            if msg is not None:
                if isinstance(msg, CumulusNative.ComputationResult):
                    return msg.deserializedResult(self.resultVDM)
            else:
                return None

    def createComputation(self, expressionText, **freeVariables):
        varNames = list(freeVariables.keys())

        expr = FORA.eval("fun(" + ",".join(varNames) + ") {" + expressionText + " } ")

        return createComputationDefinition(
                FORA.extractImplValContainer(
                    expr
                    ),
                ForaNative.makeSymbol("Call"),
                *[freeVariables[v] for v in varNames]
                )

    def submitComputation(self, expressionText, **freeVariables):
        return self.submitComputationOnClient(0, expressionText, **freeVariables)

    def submitComputationOnClient(self, clientIndex, expressionText, **freeVariables):
        if isinstance(expressionText, CumulusNative.ComputationDefinition):
            computationDefinition = expressionText
        else:
            varNames = list(freeVariables.keys())

            expr = FORA.eval("fun(" + ",".join(varNames) + ") {" + expressionText + " } ")

            computationDefinition = createComputationDefinition(
                FORA.extractImplValContainer(
                    expr
                    ),
                ForaNative.makeSymbol("Call"),
                *[freeVariables[v] for v in varNames]
                )

        computationId = self.getClient(clientIndex).createComputation(computationDefinition)

        self.getClient(clientIndex).setComputationPriority(
            computationId,
            CumulusNative.ComputationPriority(1)
            )

        return computationId

    def compute(self, expressionText, timeout = 10.0, wantsStats = False, **freeVariables):
        return self.waitForResult(
            self.submitComputation(
                expressionText,
                **freeVariables
                ),
            timeout,
            wantsStats
            )

    def waitForGlobalScheduler(self, timeout = 2.0):
        t0 = time.time()
        while self.getGlobalScheduler() is None:
            time.sleep(0.01)
            if time.time() - t0 > timeout:
                return False
        return True

    def waitForHandshake(self, timeout = 10.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if self.getWorker(0).hasEstablishedHandshakeWithExistingMachines():
                return True
            time.sleep(.01)
        return False

    def currentRegime(self):
        return self.getWorker(0).getRegimeHash()

    def waitForRegimeChange(self, oldRegime, timeout = 10.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            r = self.getWorker(0).getRegimeHash()
            if r is not None and r != oldRegime:
                return
            time.sleep(.01)
        assert False, "Timed out"

    def dumpSchedulerEventStreams(self):
        logging.info("Staring to write scheduler data due to test failure.")
        eventSets = self.extractSchedulerEventStreamsAndParameters()

        rootDir = Setup.config().rootDataDir

        data = pickle.dumps(eventSets)

        fname = "scheduler_events_" + str(HashNative.Hash.sha1(data))

        targetDir = os.path.join(rootDir, "test_failure_artifacts")

        if not os.path.isdir(targetDir):
            os.makedirs(targetDir)

        with open(os.path.join(targetDir, fname), "w") as f:
            f.write(data)

        logging.warn("Wrote scheduler data associated with test failure to %s/%s", targetDir, fname)

    def extractSchedulerEventStreamsAndParameters(self):
        eventSets = []

        for _,_,eventHandler in self.workersVdmsAndEventHandlers:
            eventSets.append(eventHandler.extractEvents())

        return eventSets


