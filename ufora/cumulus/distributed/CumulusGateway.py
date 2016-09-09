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
import uuid
import ufora.native.Hash as Hash
import ufora.native.Cumulus as CumulusNative
import ufora.distributed.Stoppable as Stoppable
import ufora.util.ManagedThread as ManagedThread

MIN_UPDATE_PERIOD = .05

SYSTEMWIDE_UPDATE_PERIOD = 2.0

class CumulusGateway(Stoppable.Stoppable):
    """Python interface with Cumulus.

    Clients should reassign "onCPUCountIncrement" and "onCPUCountDecrement"
        to get notified of cpu assignment changes.
    """
    def __init__(self, callbackScheduler, vdm, viewFactory):
        Stoppable.Stoppable.__init__(self)

        self.lock_ = threading.Lock()
        self.callbackScheduler = callbackScheduler
        self.definitionToIdMap_ = {}
        self.idToDefinitionMap_ = {}
        self.vdm = vdm

        self.onJsonViewOfSystemChanged = None

        self.persistentCacheIndex = CumulusNative.PersistentCacheIndex(
            viewFactory.createView(retrySeconds=10.0, numRetries=10),
            callbackScheduler
            )

        self.vdm.setPersistentCacheIndex(self.persistentCacheIndex)

        self.cumulusClientId = CumulusNative.CumulusClientId(Hash.Hash.sha1(str(uuid.uuid4())))

        logging.info("CumulusClient created with %s", self.cumulusClientId)

        self.cumulusClient = CumulusNative.CumulusClient(vdm, self.cumulusClientId, self.callbackScheduler)

        self.finalResponses = Queue.Queue()

        self.cumulusClientListener = self.cumulusClient.createListener()

        self.cpuAssignmentDependencyGraph = CumulusNative.CpuAssignmentDependencyGraph(
            self.callbackScheduler.getFactory().createScheduler(
                self.callbackScheduler.getMetadata() + "_cpuAssignmentGraph",
                1
                ),
            self.vdm
            )
        self.cpuAssignmentDependencyGraph.subscribeToCumulusClient(self.cumulusClient)

        self.pendingCallbacksByGuid = {}

        self.cpuAssignmentDependencyGraphListener = \
            self.cpuAssignmentDependencyGraph.createListener()

        self.threads = []

        self.threads.append(
                ManagedThread.ManagedThread(
                    target=self.processClientMessages_,
                    args=()
                    )
                )
        self.threads.append(
                ManagedThread.ManagedThread(
                    target=self.processDependencyGraphMessages_,
                    args=()
                    )
                )

        for t in self.threads:
            t.start()

        self.nextCpuUpdateTime = time.time()
        self.cpuMessagesSinceLastUpdate = 0
        self.lastSystemwideUpdateTime = time.time()


    def getClusterStatus(self):
        raise NotImplementedError("Method must be implemented by derived class")

    def bytecountForBigvecs(self, bigvecHashes):
        return self.cpuAssignmentDependencyGraph.computeBytecountForHashes(bigvecHashes)

    def setScriptRoots(self, scriptPath, computedValues):
        hashes = Hash.ImmutableTreeSetOfHash()

        for value in computedValues:
            hashes = hashes + self.getComputationIdForDefinition(value.cumulusComputationDefinition).computationHash

        logging.info("PersistentCacheIndex setting script dependencies for %s to %s hashes", scriptPath, len(hashes))
        self.persistentCacheIndex.setScriptDependencies(scriptPath, hashes)

    def triggerCheckpoint(self):
        self.cumulusClient.triggerCheckpoint()

    def subcomputationsFor(self, computationId):
        status = self.cumulusClient.currentActiveStatus(computationId)

        if status is None or not status.isBlockedOnComputations():
            return []

        return [x for x in status.asBlockedOnComputations.subthreads]

    def teardown(self):
        self.stop()

        for t in self.threads:
            t.join()

        self.vdm = None
        self.cumulusClient = None

    def processDependencyGraphMessages_(self):
        while not self.shouldStop():
            msg = self.cpuAssignmentDependencyGraphListener.getTimeout(.1)
            if msg is not None:
                self.handleCpuUpdateMessage_(msg)

            self.cpuMessagesSinceLastUpdate += 1

            if time.time() > self.nextCpuUpdateTime:
                t0 = time.time()
                self.cpuAssignmentDependencyGraph.updateDependencyGraph()

                if time.time() - t0 > 0.01:
                    logging.debug("Updating CpuAssignmentDependencyGraph took %s. There were %s messages since last update.",
                        time.time() - t0,
                        self.cpuMessagesSinceLastUpdate
                        )

                self.cpuMessagesSinceLastUpdate = 0

                delayUntilNextUpdate = max(.1, 10.0 * (time.time() - t0))

                self.nextCpuUpdateTime = time.time() + delayUntilNextUpdate

            if self.onJsonViewOfSystemChanged is not None:
                if time.time() - self.lastSystemwideUpdateTime > SYSTEMWIDE_UPDATE_PERIOD:
                    json = self.cumulusClient.getJsonViewOfSystem()
                    self.onJsonViewOfSystemChanged(json)
                    self.lastSystemwideUpdateTime = time.time()

    def triggerPerstistentCacheGarbageCollection(self, completePurge):
        self.cumulusClient.triggerCheckpointGarbageCollection(completePurge)

    def processClientMessages_(self):
        while not self.shouldStop():
            msg = self.cumulusClientListener.getTimeout(.1)
            if msg is not None:
                self.handleClientMessage_(msg)

    def createExternalIoTask(self, externalIoTask):
        return self.cumulusClient.createExternalIoTask(externalIoTask)

    def handleCpuUpdateMessage_(self, msg):
        self.onCPUCountChanged(msg)

    def handleClientMessage_(self, msg):
        if isinstance(msg, CumulusNative.ComputationResult):
            self.onComputationResult(msg.computation, msg.deserializedResult(self.vdm), msg.statistics)

        elif isinstance(msg, tuple):
            self.onCheckpointStatus(msg[0], msg[1])

        elif isinstance(msg, CumulusNative.VectorLoadedResponse):
            if not msg.loadSuccessful:
                traceback.print_stack()
                logging.info("MN>> Failure in handleClientMessage_: %s", traceback.format_exc())
                logging.critical("Page Load failed. This is not handled correctly yet. %s", msg)

            self.onCacheLoad(msg.vdid)
        elif isinstance(msg, CumulusNative.GlobalUserFacingLogMessage):
            self.onNewGlobalUserFacingLogMessage(msg)
        elif isinstance(msg, CumulusNative.ExternalIoTaskCompleted):
            self.onExternalIoTaskCompleted(msg)

    def requestComputationCheckpoint(self, computation):
        return self.cumulusClient.requestComputationCheckpoint(computation)

    def requestCheckpointStatusAndReturnGuid(self):
        return self.cumulusClient.requestCheckpointStatus()

    def onNewGlobalUserFacingLogMessage(self, msg):
        pass

    def onExternalIoTaskCompleted(self, msg):
        pass

    def onComputationResult(self, computationId, computationResult, statistics):
        self.finalResponses.put((computationId, computationResult, statistics))

    def onCheckpointStatus(self, requestGuid, checkpointStatusJson):
        pass

    def onCPUCountChanged(self, computationSystemwideCpuAssignment):
        pass

    def onCacheLoad(self, cacheLoadVectorDataID):
        pass

    def onMachineCountWentToZero(self):
        pass

    def requestCacheItem(self, vectorDataID):
        self.cumulusClient.requestVectorLoad(
            CumulusNative.VectorLoadRequest(
                vectorDataID
                )
            )

    def requestComputation(self, computationDefinition):
        with self.lock_:
            oldId, id = self.getNewComputationIdForDefinition_(computationDefinition)

            self.setComputationPriority_(id, CumulusNative.ComputationPriority(1))
            return id

    def deprioritizeComputation(self, computationId):
        self.setComputationPriority(computationId, CumulusNative.ComputationPriority())

    def resetStateCompletely(self):
        self.cumulusClient.resetComputationState()

    def setComputationPriority(self, computationId, computationPriority):
        with self.lock_:
            self.setComputationPriority_(computationId, computationPriority)

    def setComputationPriority_(self, computationId, computationPriority):
        self.cumulusClient.setComputationPriority(computationId, computationPriority)

        if computationPriority == CumulusNative.ComputationPriority():
            self.cpuAssignmentDependencyGraph.markNonrootComputation(computationId)
        else:
            self.cpuAssignmentDependencyGraph.markRootComputation(computationId)

    def getNewComputationIdForDefinition(self, computationDefinition):
        with self.lock_:
            return self.getNewComputationIdForDefinition_(computationDefinition)

    def getNewComputationIdForDefinition_(self, computationDefinition):
        oldId = None

        if computationDefinition in self.definitionToIdMap_:
            oldId = self.definitionToIdMap_[computationDefinition]

        compId = self.cumulusClient.createComputation(computationDefinition)

        self.definitionToIdMap_[computationDefinition] = compId
        self.idToDefinitionMap_[compId] = computationDefinition

        return oldId, compId

    def getComputationIdForDefinition(self, computationDefinition):
        with self.lock_:
            return self.getComputationIdForDefinition_(computationDefinition)

    def getComputationIdForDefinition_(self, computationDefinition):
        if computationDefinition not in self.definitionToIdMap_:
            compId = self.cumulusClient.createComputation(computationDefinition)

            self.definitionToIdMap_[computationDefinition] = compId
            self.idToDefinitionMap_[compId] = computationDefinition

        return self.definitionToIdMap_[computationDefinition]


