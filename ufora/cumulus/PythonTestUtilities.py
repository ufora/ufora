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
import logging

import ufora.native.FORA as ForaNative
import ufora.native.Hash as HashNative
import ufora.native.Cumulus as CumulusNative
import ufora.native.StringChannel as StringChannelNative
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.FORA.python.FORA as FORA
import ufora.config.Setup as Setup


import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.SharedState.Connections.InMemoryChannelFactory as InMemorySharedStateChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.cumulus.distributed.PythonIoTaskService as PythonIoTaskService
import ufora.distributed.Storage.S3ObjectStore as S3ObjectStore


IN_MEMORY_CLUSTER_SS_PING_INTERVAL = 10.0

def machineId(ix):
    return CumulusNative.MachineId(HashNative.Hash(ix))

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

def createWorker(machineId, viewFactory, callbackSchedulerToUse = None, threadCount = 2, memoryLimitMb = 100):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    vdm = ForaNative.VectorDataManager(callbackSchedulerToUse, 5 * 1024 * 1024)
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

    cache = CumulusNative.SimpleOfflineCache(callbackSchedulerToUse, 1000 * 1024 * 1024)

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

def createClient(clientId, callbackSchedulerToUse = None):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    vdm = ForaNative.VectorDataManager(callbackSchedulerToUse, 5 * 1024 * 1024)
    vdm.setMemoryLimit(100 * 1024 * 1024, 125 * 1024 * 1024)

    return (
        CumulusNative.CumulusClient(vdm, clientId, callbackSchedulerToUse),
        vdm
        )

def createWorkersAndClients(
            workerCount,
            clientCount,
            viewFactory = None,
            memoryLimitMb = 100,
            threadCount = 2,
            callbackSchedulerToUse = None
            ):
    if callbackSchedulerToUse is None:
        callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    if viewFactory is None:
        viewFactory = createInMemorySharedStateViewFactory(callbackSchedulerToUse)

    workersVdmsAndEventHandlers = [
        createWorker(
            machineId(ix),
            viewFactory,
            memoryLimitMb = memoryLimitMb,
            threadCount=threadCount,
            callbackSchedulerToUse = callbackSchedulerToUse
            ) for ix in range(workerCount)
        ]

    clientsAndVdms = [
        createClient(
            clientId(ix),
            callbackSchedulerToUse = callbackSchedulerToUse
            )
        for ix in range(clientCount)
        ]

    for ix1 in range(len(workersVdmsAndEventHandlers)):
        workersVdmsAndEventHandlers[ix1][0].startComputations()

    for ix1 in range(len(workersVdmsAndEventHandlers)-1):
        for ix2 in range(ix1 + 1, len(workersVdmsAndEventHandlers)):
            worker1Channel1, worker2Channel1 = StringChannelNative.InMemoryStringChannel(callbackSchedulerToUse)
            worker1Channel2, worker2Channel2 = StringChannelNative.InMemoryStringChannel(callbackSchedulerToUse)
            workersVdmsAndEventHandlers[ix1][0].addMachine(machineId(ix2), [worker1Channel1, worker1Channel2], ForaNative.ImplValContainer(), callbackSchedulerToUse)
            workersVdmsAndEventHandlers[ix2][0].addMachine(machineId(ix1), [worker2Channel1, worker2Channel2], ForaNative.ImplValContainer(), callbackSchedulerToUse)

    for ix1 in range(len(workersVdmsAndEventHandlers)):
        for ix2 in range(len(clientsAndVdms)):
            workerChannel1, clientChannel1 = StringChannelNative.InMemoryStringChannel(callbackSchedulerToUse)
            workerChannel2, clientChannel2 = StringChannelNative.InMemoryStringChannel(callbackSchedulerToUse)
            workersVdmsAndEventHandlers[ix1][0].addCumulusClient(clientId(ix2), [workerChannel1, workerChannel2], ForaNative.ImplValContainer(), callbackSchedulerToUse)
            clientsAndVdms[ix2][0].addMachine(machineId(ix1), [clientChannel1, clientChannel2], ForaNative.ImplValContainer(), callbackSchedulerToUse)

    return workersVdmsAndEventHandlers, clientsAndVdms, viewFactory

def waitForResult(listener, computation, vdm, timeout = 1.0, wantsStats = False):
    while True:
        msg = listener.getTimeout(timeout)

        if msg is None:
            return msg


        if (isinstance(msg, CumulusNative.ComputationResult)
                    and msg.computation == computation):
            if wantsStats:
                return msg.deserializedResult(vdm), msg.statistics
            else:
                return msg.deserializedResult(vdm)

def createComputationDefinition(*args):
    return CumulusNative.ComputationDefinition.Root(
                CumulusNative.ImmutableTreeVectorOfComputationDefinitionTerm(
                    [CumulusNative.ComputationDefinitionTerm.Value(ForaNative.ImplValContainer(x), None)
                        for x in args]
                    )
                )

def blockUntilWorkerIsConnected(worker, timeout):
    t0 = time.time()

    while not worker.hasEstablishedHandshakeWithExistingMachines():
        time.sleep(0.01)

        if time.time() - t0 > timeout:
            raise UserWarning("Failed to connect to worker in %s seconds" % timeout)

def submitAdditionalComputation(simulationDict, expressionText, timeout = 10.0, wantsStats = False):
    client = simulationDict["client"]

    computationId = client.createComputation(
        createComputationDefinition(
            FORA.extractImplValContainer(
                FORA.eval("fun() {" + expressionText + " } ")
                ),
            ForaNative.makeSymbol("Call")
            )
        )

    client.setComputationPriority(
        computationId,
        CumulusNative.ComputationPriority(1)
        )

    return computationId

def evaluateComputationInSimulation(simulationDict, expressionText, timeout=10.0, wantsStats=False):
    computationId = submitAdditionalComputation(simulationDict, expressionText, timeout, wantsStats)

    assert isinstance(simulationDict['clientsAndVdms'][0][1], ForaNative.VectorDataManager)

    return waitForResult(
        simulationDict["listener"],
        computationId,
        simulationDict['clientsAndVdms'][0][1],
        timeout = timeout,
        wantsStats = wantsStats
        )

def computeUsingSeveralWorkers(expressionText,
                               s3Service,
                               count,
                               objectStore=None,
                               wantsStats=False,
                               timeout=10,
                               returnEverything=False,
                               memoryLimitMb=100,
                               blockUntilConnected=False,
                               keepSimulationAlive=False,
                               sharedStateViewFactory=None,
                               threadCount=2):
    if keepSimulationAlive:
        assert returnEverything, \
            "can't keep the simulation alive and not return it. how would you shut it down?"

    callbackSchedulerToUse = CallbackScheduler.singletonForTesting()

    if sharedStateViewFactory is None:
        sharedStateViewFactory = createInMemorySharedStateViewFactory(
                                    callbackSchedulerToUse = callbackSchedulerToUse
                                    )

    workersVdmsAndEventHandlers, clientsAndVdms, viewFactory = (
        createWorkersAndClients(
            count,
            1,
            sharedStateViewFactory,
            memoryLimitMb = memoryLimitMb,
            threadCount = threadCount
            )
        )

    client = clientsAndVdms[0][0]
    clientVdm = clientsAndVdms[0][1]

    loadingServices = []

    for ix in range(len(workersVdmsAndEventHandlers)):
        worker = workersVdmsAndEventHandlers[ix][0]
        workerVdm = workersVdmsAndEventHandlers[ix][1]

        s3InterfaceFactory = s3Service.withMachine(ix)
        if objectStore is None:
            objectStore = S3ObjectStore.S3ObjectStore(
                s3InterfaceFactory,
                Setup.config().userDataS3Bucket,
                prefix="test/")

        loadingService = PythonIoTaskService.PythonIoTaskService(
            s3InterfaceFactory,
            objectStore,
            workerVdm,
            worker.getExternalDatasetRequestChannel(callbackSchedulerToUse).makeQueuelike(callbackSchedulerToUse)
            )
        loadingService.startService()

        loadingServices.append(loadingService)

    if blockUntilConnected:
        for worker,vdm,eventHandler in workersVdmsAndEventHandlers:
            blockUntilWorkerIsConnected(worker, 2.0)

    if isinstance(expressionText, CumulusNative.ComputationDefinition):
        computationDefinition = expressionText
    else:
        computationDefinition = (
            createComputationDefinition(
                FORA.extractImplValContainer(
                    FORA.eval("fun() {" + expressionText + " } ")
                    ),
                ForaNative.makeSymbol("Call")
                )
            )

    teardownGates = []
    for client, vdm in clientsAndVdms:
        teardownGates.append(vdm.getVdmmTeardownGate())

    for worker, vdm, eventHandler in workersVdmsAndEventHandlers:
        teardownGates.append(vdm.getVdmmTeardownGate())

    simulationDict = {
        "result": None,
        "timedOut": None,
        "stats": None,
        "clientsAndVdms": clientsAndVdms,
        "workersVdmsAndEventHandlers": workersVdmsAndEventHandlers,
        "s3Service": s3Service,
        "loadingServices": loadingServices,
        "sharedStateViewFactory": sharedStateViewFactory,
        "client": client,
        "teardownGates": teardownGates
        }
    try:
        listener = client.createListener()

        computationSubmitTime = time.time()

        computationId = client.createComputation(computationDefinition)

        client.setComputationPriority(
            computationId,
            CumulusNative.ComputationPriority(1)
            )

        if returnEverything:
            valAndStatsOrNone = waitForResult(listener, computationId, clientVdm, timeout=timeout, wantsStats=True)

            computationReturnTime = time.time()

            if valAndStatsOrNone is None:
                #we timed out
                val = None
                stats = None
                timedOut = True
            else:
                val, stats = valAndStatsOrNone
                timedOut = False

            simulationDict.update({
                "result": val,
                "stats": stats,
                "timedOut": timedOut,
                "computationId": computationId,
                "listener": listener,
                "totalTimeToReturnResult": computationReturnTime - computationSubmitTime
                })

            return simulationDict
        else:
            return waitForResult(listener, computationId, clientVdm, timeout=timeout, wantsStats=wantsStats)
    finally:
        if not keepSimulationAlive:
            teardownSimulation(simulationDict)

def teardownSimulation(simulationDict):
    for service in simulationDict["loadingServices"]:
        service.stopService()

    for worker,vdm,eventHandler in simulationDict["workersVdmsAndEventHandlers"]:
        worker.teardown()



def dumpSchedulerEventStreams(simulationDict):
    eventSets = extractSchedulerEventStreamsAndParameters(simulationDict)

    rootDir = Setup.config().rootDataDir

    data = pickle.dumps(eventSets)

    fname = "scheduler_events_" + str(HashNative.Hash.sha1(data))

    targetDir = os.path.join(rootDir, "test_failure_artifacts")

    if not os.path.isdir(targetDir):
        os.makedirs(targetDir)

    with open(os.path.join(targetDir, fname), "w") as f:
        f.write(data)

    logging.warn("Wrote scheduler data associated with test failure to %s/%s", targetDir, fname)

def extractSchedulerEventStreamsAndParameters(simulationDict):
    eventSets = []

    for _,_,eventHandler in simulationDict["workersVdmsAndEventHandlers"]:
        eventSets.append(eventHandler.extractEvents())

    return eventSets



