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

"""Maintains a background loop for submitting ComputedValue work to Cumulus"""
import threading
import logging

import ufora.util.DefaultDict as DefaultDict
import ufora.distributed.Stoppable as Stoppable
import ufora.config.Setup as Setup
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedGraph.BackgroundUpdateQueue as BackgroundUpdateQueue
import ufora.native.Cumulus as CumulusNative
import ufora.util.ThreadLocalStack as ThreadLocalStack
import traceback

from ufora.BackendGateway.CacheLoader import CacheLoader

ViewOfEntireCumulusSystem = None
PersistentCacheIndex = None

class ComputedValueGateway(ThreadLocalStack.ThreadLocalStackPushable):
    def __init__(self):
        ThreadLocalStack.ThreadLocalStackPushable.__init__(self)

    def increaseRequestCount(self, compValue, cumulusComputationDefinition):
        assert False, "Subclass should implement"

    def decreaseRequestCount(self, cumulusComputationDefinition):
        assert False, "Subclass should implement"

    def decreaseVectorRequestCount(self, vectorCGLocation):
        assert False, "Subclass should implement"

    def increaseVectorRequestCount(self, vectorCGLocation):
        assert False, "Subclass should implement"

    def teardown(self):
        assert False, "Subclass should implement"



class CumulusComputedValueGateway(CacheLoader, ComputedValueGateway, Stoppable.Stoppable):
    """Gateway - a global object that manages the interface between
    Cumulus and ComputedValue.

    We submit requests with a priority level
    that's a pair (index, hash) where 'index' is an index that increases
    every time we submit new work and 'hash' is a randomly generated
    unique hash that we can use to see what's checked out in cumulus.

    """

    def __init__(self, callbackScheduler, cumulusGatewayFactory):
        self.callbackScheduler = callbackScheduler
        ComputedValueGateway.__init__(self)

        Stoppable.Stoppable.__init__(self)

        CacheLoader.__init__(
            self,
            callbackSchedulerFactory,
            callbackScheduler,
            Setup.config().computedValueGatewayRAMCacheMB * 1024 * 1024
            )

        logging.info("cumulusGatewayFactory is %s", cumulusGatewayFactory)

        self.cumulusGateway = cumulusGatewayFactory(self.callbackScheduler, self.vdm)
        self.externalIoTaskCallbacks_ = {}

        self.refcountTracker = self.cumulusGateway.cumulusClient.getSystemwidePageRefcountTracker()

        self.cumulusGateway.onNewGlobalUserFacingLogMessage = self.onNewGlobalUserFacingLogMessage
        self.cumulusGateway.onExternalIoTaskCompleted = self.onExternalIoTaskCompleted
        self.cumulusGateway.onCPUCountChanged = self.onCPUCountChanged
        self.cumulusGateway.onComputationResult = self.onComputationResult
        self.cumulusGateway.onMachineCountWentToZero = self.onMachineCountWentToZero

        self.refcountsForCompIds_ = DefaultDict.DefaultDict(lambda computedValue: 0)

        self.computedValuesForComputations = {}
        self.finishedResultsForComputations = {}

        self.curPriorityIndex = 0

        self.lock_ = threading.RLock()

        assert ComputedGraph.currentGraph() is not None

        self.cumulusGateway.onJsonViewOfSystemChanged = self.onJsonViewOfSystemChanged



    def teardown(self):
        self.stop()

        self.cumulusGateway.teardown()

        self.cumulusGateway = None
        self.vdm = None

    def onJsonViewOfSystemChanged(self, json):
        def updater():
            global ViewOfEntireCumulusSystem
            global PersistentCacheIndex
            if ViewOfEntireCumulusSystem is None:
                import ufora.BackendGateway.ComputedValue.ViewOfEntireCumulusSystem as ViewOfEntireCumulusSystem
                import ufora.BackendGateway.ComputedValue.PersistentCacheIndex as PersistentCacheIndex

            ViewOfEntireCumulusSystem.ViewOfEntireCumulusSystem().viewOfSystem_ = json.toSimple()
            PersistentCacheIndex.PersistentCacheIndex().update()

        BackgroundUpdateQueue.push(updater)

    def onExternalIoTaskCompleted(self, msg):
        taskGuid = msg.taskId.guid
        with self.lock_:
            if taskGuid not in self.externalIoTaskCallbacks_:
                logging.warn("TaskId %s was not found in the task guid list", taskGuid)
                return

            callback = self.externalIoTaskCallbacks_[taskGuid]
            del self.externalIoTaskCallbacks_[taskGuid]

            def executor():
                callback(msg.result)

            BackgroundUpdateQueue.push(executor)

    def createExternalIoTask(self, externalIoTask, callback):
        taskIdGuid = self.cumulusGateway.createExternalIoTask(externalIoTask).guid
        with self.lock_:
            self.externalIoTaskCallbacks_[taskIdGuid] = callback

    def onNewGlobalUserFacingLogMessage(self, newMsg):
        def updater():
            global ViewOfEntireCumulusSystem
            global PersistentCacheIndex
            if ViewOfEntireCumulusSystem is None:
                import ufora.BackendGateway.ComputedValue.ViewOfEntireCumulusSystem as ViewOfEntireCumulusSystem
                import ufora.BackendGateway.ComputedValue.PersistentCacheIndex as PersistentCacheIndex

            ViewOfEntireCumulusSystem.ViewOfEntireCumulusSystem().pushNewGlobalUserFacingLogMessage(newMsg)

        BackgroundUpdateQueue.push(updater)

    def onComputationResult(self, computationId, result, statistics):
        with self.lock_:
            self.finishedResultsForComputations[computationId] = (result, statistics)
            if computationId in self.computedValuesForComputations:
                for compVal in self.computedValuesForComputations[computationId]:
                    BackgroundUpdateQueue.push(
                        self.valueUpdater(
                            compVal,
                            result,
                            statistics
                            )
                        )


    def onCPUCountChanged(self, computationSystemwideCpuAssignment):
        with self.lock_:
            computationId = computationSystemwideCpuAssignment.computation

            if computationId in self.computedValuesForComputations:
                for compVal in self.computedValuesForComputations[computationId]:
                    BackgroundUpdateQueue.push(
                        self.cpuCountSetter_(
                            compVal,
                            computationSystemwideCpuAssignment
                            )
                        )

    def cpuCountSetter_(self, compVal, computationSystemwideCpuAssignment):
        """return a lambda function that increments the worker count of
        'compVal' (a ComputedValue) in the BackgroundUpdateQueue.
        """
        rootComputedValueDependencies = []
        for compId in computationSystemwideCpuAssignment.rootComputationDependencies:
            if compId in self.computedValuesForComputations:
                for cv in self.computedValuesForComputations[compId]:
                    rootComputedValueDependencies.append(cv)

        def setCpuCounts():
            cpus = computationSystemwideCpuAssignment
            compVal.workerCount = cpus.cpusAssignedDirectly
            compVal.workerCountForDependentComputations = cpus.cpusAssignedToChildren
            compVal.cacheloadCount = cpus.cacheloadsAssignedDirectly
            compVal.cacheloadCountForDependentComputations = cpus.cacheloadsAssignedToChildren
            compVal.checkpointStatus = cpus.checkpointStatus
            compVal.totalComputeSecondsAtLastCheckpoint = cpus.totalComputeSecondsAtLastCheckpoint
            compVal.isCheckpointing = cpus.isCheckpointing
            compVal.isLoadingFromCheckpoint = cpus.isLoadingFromCheckpoint
            compVal.rootComputedValueDependencies = tuple(rootComputedValueDependencies)
            compVal.totalBytesReferencedAtLastCheckpoint = cpus.totalBytesReferencedAtLastCheckpoint


        return setCpuCounts

    def bytecountForBigvecs(self, bigvecHashSet):
        return self.cumulusGateway.bytecountForBigvecs(bigvecHashSet)

    def onMachineCountWentToZero(self):
        pass

    def getPersistentCacheIndex(self):
        return self.cumulusGateway.persistentCacheIndex

    def triggerPerstistentCacheGarbageCollection(self, completePurge):
        self.cumulusGateway.triggerPerstistentCacheGarbageCollection(completePurge)

    def setScriptRoots(self, scriptPath, computedValues):
        """Push the sha-hashes of the given computedValues into the persistent cache index,
        indicating to the infrastructure that these calculations are important and should
        have a higher important in the GC process.
        """
        self.cumulusGateway.setScriptRoots(scriptPath, computedValues)

    def resetStateEntirely(self):
        """Cancel all computations and clear the compute cache."""
        self.cancelAllComputations(True)

        with self.lock_:
            computations = list(self.refcountsForCompIds_.keys())

            for computationId in computations:
                if computationId in self.finishedResultsForComputations:
                    del self.finishedResultsForComputations[computationId]
                for compVal in self.computedValuesForComputations[computationId]:
                    BackgroundUpdateQueue.push(
                        self.valueUpdater(
                            compVal,
                            None,
                            None
                            )
                        )

            for vecId in self.vectorDataIDToVectorSlices_:
                for cgLocation in self.vectorDataIDToVectorSlices_[vecId]:
                    BackgroundUpdateQueue.push(self.createSetIsLoadedFun(cgLocation, False))

            self.vectorDataIDRequestCount_ = {}
            self.vectorDataIDToVectorSlices_ = {}

    def submittedComputationId(self, definition):
        return self.cumulusGateway.getComputationIdForDefinition(definition)

    def cancelAllComputations(self, resetCompletely = False):
        with self.lock_:
            for compId, refcount in self.refcountsForCompIds_.iteritems():
                if refcount > 0:
                    self.cumulusGateway.setComputationPriority(
                        compId,
                        CumulusNative.ComputationPriority()
                        )
                    self.refcountsForCompIds_[compId] = 0

            if resetCompletely:
                self.cumulusGateway.resetStateCompletely()


    def cancelComputation(self, compValue, cumulusComputationDefinition):
        computationId = self.cumulusGateway.getComputationIdForDefinition(
                        cumulusComputationDefinition
                        )

        with self.lock_:
            if computationId in self.refcountsForCompIds_ and self.refcountsForCompIds_[computationId] > 0:
                self.refcountsForCompIds_[computationId] = 0
                self.cumulusGateway.setComputationPriority(
                    computationId,
                    CumulusNative.ComputationPriority()
                    )

    def requestComputationCheckpoint(self, compValue, cumulusComputationDefinition):
        computationId = self.cumulusGateway.getComputationIdForDefinition(
                        cumulusComputationDefinition
                        )

        self.cumulusGateway.requestComputationCheckpoint(computationId)


    def increaseRequestCount(self, compValue, cumulusComputationDefinition):
        computationId = self.cumulusGateway.getComputationIdForDefinition(
                        cumulusComputationDefinition
                        )

        with self.lock_:
            if computationId not in self.computedValuesForComputations:
                self.computedValuesForComputations[computationId] = set()
            self.computedValuesForComputations[computationId].add(compValue)

            self.refcountsForCompIds_[computationId] += 1
            if self.refcountsForCompIds_[computationId] == 1:
                self.cumulusGateway.setComputationPriority(
                    computationId,
                    CumulusNative.ComputationPriority(self.allocNewPriority_())
                    )

            if computationId in self.finishedResultsForComputations:
                result, statistics = self.finishedResultsForComputations[computationId]
                BackgroundUpdateQueue.push(
                    self.valueUpdater(
                        compValue,
                        result,
                        statistics
                        )
                    )

    def allocNewPriority_(self):
        self.curPriorityIndex += 1
        return self.curPriorityIndex

    def decreaseRequestCount(self, compValue, cumulusComputationDefinition):
        computationId = self.cumulusGateway.getComputationIdForDefinition(
                        cumulusComputationDefinition
                        )

        with self.lock_:
            if computationId in self.refcountsForCompIds_ and self.refcountsForCompIds_[computationId] > 0:
                self.refcountsForCompIds_[computationId] -= 1

                if self.refcountsForCompIds_[computationId] == 0:
                    self.cumulusGateway.setComputationPriority(
                        computationId,
                        CumulusNative.ComputationPriority()
                        )



    def valueUpdater(self, computedValue, foraComputationResult, statistics):
        def updateComputedValueResult():
            computedValue.result = foraComputationResult
            computedValue.computationStatistics = statistics
            computedValue.workerCount = 0
            computedValue.workerCountForDependentComputations = 0
            computedValue.cacheloadCount = 0
            computedValue.cacheloadCountForDependentComputations = 0

        return updateComputedValueResult


class DummyGateway(ComputedValueGateway):
    def __init__(self):
        ComputedValueGateway.__init__(self)

    def increaseRequestCount(self, *args):
        pass

    def decreaseRequestCount(self, *args):
        pass

    def teardown(self, *args):
        pass

    def decreaseVectorRequestCount(self, vectorCGLocation):
        pass

    def increaseVectorRequestCount(self, vectorCGLocation):
        pass


def getGateway():
    return ComputedValueGateway.getCurrent()

