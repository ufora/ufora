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

"""LocalEvaluator

Evaluates FORA code in the local process.
"""

import ufora.config.Setup as Setup
import ufora.distributed.Stoppable as Stoppable
import ufora.native.FORA as FORANative
import ufora.native.Cumulus as CumulusNative
import ufora.native.CallbackScheduler as CallbackSchedulerNative
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.Evaluator.EvaluatorBase as EvaluatorBase
import ufora.FORA.python.CacheSemantics as CacheSemantics
import ufora.util.ManagedThread as ManagedThread
import ufora.util.TwoWaySetMap as TwoWaySetMap
import ufora.FORA.python.PythonIoTasks as PythonIoTasks
import ufora.util.OutOfProcessDownloader as OutOfProcessDownloader
import ufora.distributed.S3.ActualS3Interface as ActualS3Interface
import threading
import traceback
import logging
import Queue
import time

#FORA constants and types
ComputationResult_ = FORANative.ComputationResult
ImplValContainer_ = FORANative.ImplValContainer
symbol_Call_ = FORANative.symbol_Call

kMinSplitTimeInterval = .05
kThreadWorkerWakeupLoopTimeInterval = .01

DISABLE_SPLITTING = False

#lock around copying values in/out of the Free Store
freestoreLock = threading.Lock()

class SplitResult(object):
    def __init__(self, inFuturesSplitResult, inComputationsToSlotIndices):
        self.futuresSplitResult = inFuturesSplitResult
        self.computationsToSlotIndices = inComputationsToSlotIndices

    def submittedComputations(self):
        return self.computationsToSlotIndices.keys()

def getCurrentS3Interface():
    return ActualS3Interface.ActualS3InterfaceFactory()

class ComputationCache(Stoppable.Stoppable):
    def __init__(self, vdm, offlineCache):
        Stoppable.Stoppable.__init__(self)
        self.dependencies_ = TwoWaySetMap.TwoWaySetMap()
        self.vdm_ = vdm
        self.offlineCache_ = offlineCache
        self.finishedValues_ = {}
        self.intermediates_ = {}
        self.lock_ = threading.RLock()
        self.completable_ = Queue.Queue()
        self.timesComputed = 0
        self.computingContexts_ = {}
        self.computingContexts_t0_ = {}
        self.isSplit_ = set()
        self.watchers_ = {}
        self.contexts_ = []

        self.inProcessDownloader = (
            OutOfProcessDownloader.OutOfProcessDownloaderPool(
                Setup.config().cumulusServiceThreadCount,
                actuallyRunOutOfProcess = False
                )
            )

        self.threads_ = []
        self.isActive = True
        #setup the primary cache object, and set its worker threads going
        for threadIx in range(Setup.config().cumulusServiceThreadCount):
            workerThread = ManagedThread.ManagedThread(target = self.threadWorker)
            workerThread.start()
            self.threads_.append(workerThread)


    def flush(self):
        self.finishedValues_ = {}
        self.contexts_ = []

    def teardown(self):
        self.stop()
        self.inProcessDownloader.teardown()
        for t in self.threads_:
            t.join()
        self.offlineStorage = None
        self.threads_ = []
        self.isActive = False
        self.vdm_ = None
        self.contexts_ = []
        self.finishedValues_ = {}
        self.intermediates_ = {}
        self.computingContexts_ = {}
        self.computingContexts_t0_ = {}
        self.isSplit_ = set()
        self.dependencies_ = None

    def contextEnterer(cache, context):
        class TR(object):
            def __enter__(self):
                with cache.lock_:
                    cache.computingContexts_t0_[id(context)] = time.time()
                    cache.computingContexts_[id(context)] = context
            def __exit__(self, *args):
                with cache.lock_:
                    del cache.computingContexts_[id(context)]
                    del cache.computingContexts_t0_[id(context)]
        return TR()

    def grabContext(self):
        """get an execution context"""
        with self.lock_:
            if not self.contexts_:
                context = ExecutionContext.ExecutionContext(
                    dataManager = self.vdm_
                    )
            else:
                context = self.contexts_.pop()
        return context

    def checkContextBackIn(self, context):
        """check an execution context back into the pool"""
        context.teardown()
        self.contexts_.append(context)

    def cacheLookup(self, computationToCall, leaveInCache = True):
        return self.cacheLookupSeveral(self, [computationToCall], leaveInCache = leaveInCache)[0]

    def cacheLookupSeveral(self, computationsToCall, block = True, leaveInCache = True):
        with self.lock_:
            notAlreadyInCache = [
                comp for comp in computationsToCall
                    if comp not in self.finishedValues_ and comp not in self.intermediates_
                ]

            for comp in computationsToCall:
                #put it in the cache if its not there already
                if comp not in self.finishedValues_ and comp not in self.intermediates_:
                    self.intermediates_[comp] = None
                    self.completable_.put(comp)
                    self.watchers_[comp] = threading.Event()

            allDone = True
            for comp in computationsToCall:
                if comp not in self.finishedValues_:
                    allDone = False

        #wait until the event is set. at this point the value should
        #be filled out
        if not allDone and block:
            for comp in computationsToCall:
                self.watchers_[comp].wait()
            allDone = True

        if allDone:
            result = [self.finishedValues_[comp] for comp in computationsToCall]

            if not leaveInCache:
                for c in notAlreadyInCache:
                    del self.finishedValues_[c]

            return result
        else:
            return None


    def threadWorker(self):
        while not self.shouldStop():
            try:
                toCompute = self.completable_.get(True, kThreadWorkerWakeupLoopTimeInterval)
                self.timesComputed += 1
                self.computeOneNode(toCompute)
            except Queue.Empty:
                #we didn't see anything in the compute cache to work on, so
                #we split anything that's computing, in the expectation that we
                #will then have something to do.
                with self.lock_:
                    if self.intermediates_ and not self.computingContexts_ and \
                            self.completable_.qsize() == 0:
                        #check whether we have a cycle in the dependencies
                        #a random walk should terminate in a cycle
                        curNode = list(self.intermediates_.keys())[0]
                        curNodeList = [curNode]
                        curNodeSet = set(curNodeList)

                        while curNode is not None:
                            deps = self.dependencies_[curNode]
                            if not deps:
                                curNode = None
                            else:
                                curNode = list(deps)[0]
                                if curNode in curNodeSet:
                                    #we found a loop. backtrack until we find it
                                    ix = curNodeList.index(curNode)
                                    loop = curNodeList[ix:]

                                    #first, we need to take each of these nodes out of
                                    #each others dependency list
                                    for l in loop:
                                        self.dependencies_[l] = set()

                                    for l in loop:
                                        self.finishNode_(l,
                                            ComputationResult_.Exception(
                                                ImplValContainer_(
                                                    ("cyclic cachecall detected",
                                                        FORANative.emptyStackTrace
                                                        )
                                                    ),
                                                ImplValContainer_()
                                                )
                                            )
                                    curNode = None
                                else:
                                    curNodeSet.add(curNode)
                                    curNodeList.append(curNode)

                    for x in self.computingContexts_:
                        try:
                            if ((time.time() - self.computingContexts_t0_[x]) >
                                                kMinSplitTimeInterval and not DISABLE_SPLITTING):
                                if not self.computingContexts_[x].isTracing():
                                    self.isSplit_.add(x)
                                    self.computingContexts_[x].interrupt()
                                    self.computingContexts_t0_[x] = time.time()
                        except:
                            traceback.print_exc()
            except:
                traceback.print_exc()

    def timeElapsedForContext(self, c):
        return c.getTimeSpentInInterpreter() + c.getTimeSpentInCompiledCode()

    def finishNode_(self, node, result):
        with self.lock_:
            self.finishedValues_[node] = result
            del self.intermediates_[node]

            depsOnMe = list(self.dependencies_.keysFor(node))
            self.dependencies_.dropValue(node)
            for d in depsOnMe:
                if not self.dependencies_[d]:
                    self.completable_.put(d)
            self.watchers_[node].set()

    def checkShouldSplit(self, context):
        with self.lock_:
            if id(context) in self.isSplit_:
                self.isSplit_.discard(id(context))

                #now see if we've spent enough time to justify splitting
                if self.timeElapsedForContext(context) > kMinSplitTimeInterval:
                    return True

        return False

    def findMeatyPausedComputations(self, futuresSplitResult):
        submittableFutures = futuresSplitResult.indicesOfSubmittableFutures()
        pausedComputationsWithIndicesToInspect = set(map(
            lambda ix: (futuresSplitResult.pausedComputationForSlot(ix), ix),
            submittableFutures))

        meatyPausedComputationsAndIndices = []
        inspectedIndices = set()

        loopCt = 0
        while len(pausedComputationsWithIndicesToInspect) > 0:
            loopCt += 1

            pausedComputationAndIx = pausedComputationsWithIndicesToInspect.pop()

            slotIx = pausedComputationAndIx[1]

            quickContext = self.grabContext()
            quickContext.resumePausedComputation(pausedComputationAndIx[0])
            quickContext.resetInterruptState()
            quickContext.interruptAfterCycleCount(1000)
            quickContext.resume()

            nIter = 0
            while True:
                nIter += 1
                if quickContext.isInterrupted() or quickContext.isVectorLoad() or quickContext.isCacheRequest():
                    meatyPausedComputationsAndIndices.append(pausedComputationAndIx)
                    inspectedIndices.add(slotIx)

                    self.checkContextBackIn(quickContext)
                    break
                elif quickContext.isFinished():
                    result = quickContext.getFinishedResult()

                    futuresSplitResult.slotCompleted(slotIx, result)
                    futuresSplitResult.continueSimulation()
                    inspectedIndices.add(slotIx)

                    currentSubmittableFutures = futuresSplitResult.indicesOfSubmittableFutures()
                    for newIx in set(currentSubmittableFutures).difference(inspectedIndices):
                        #print "found new work at ix = %s" % newIx
                        pausedComputationsWithIndicesToInspect.add(
                            (futuresSplitResult.pausedComputationForSlot(newIx), newIx))

                    self.checkContextBackIn(quickContext)
                    break
                if nIter > 10000:
                    assert False, "spun too many times!"

        if len(meatyPausedComputationsAndIndices) > 0:
            return False, meatyPausedComputationsAndIndices
        else:
            return True, futuresSplitResult.getFinalResult()

    def computeIntermediatesForSplitResult(
            self, node, futuresSplitResult, meatyPausedComputationsAndIndices):
        deps = set()
        computationsToSlotIndices = dict()

        for pausedComputationAndIx in meatyPausedComputationsAndIndices:
            pausedComputation = pausedComputationAndIx[0]
            ix = pausedComputationAndIx[1]

            self.intermediates_[pausedComputation] = None
            self.completable_.put(pausedComputation)
            self.watchers_[pausedComputation] = threading.Event()
            deps.add(pausedComputation)
            computationsToSlotIndices[pausedComputation] = ix

        self.dependencies_[node] = deps

        return SplitResult(futuresSplitResult, computationsToSlotIndices)

    def computeOneNode(self, node):
        """push 'node' one step further in its computation requirements

        self.intermediates_[node] either contains a list of values to be computed
        or an execution context
        """

        if self.intermediates_[node] is None:
            context = self.grabContext()

            #the intermediates can either be None or
            #an execution context. in this case, since its a list
            #we have not even started computation yet, so we need to create
            #an ExecutionContext and begin computing
            with self.contextEnterer(context):
                context.resetInterruptState()
                if isinstance(node, tuple):
                    with freestoreLock:
                        #this operation may be copying values in the freestore as we're
                        #updating them, so we need to do it under a lock
                        context.placeInEvaluationStateWithoutRenamingMutableVectors(*node)
                    context.resume()

                elif isinstance(node, FORANative.PausedComputation):
                    context.resumePausedComputation(node)
                    context.resetInterruptState()
                    context.resume()
                else:
                    assert False, "don't know what to do with node of type %s" % node

            self.intermediates_[node] = context

        elif isinstance(self.intermediates_[node], FORANative.ExecutionContext):
            #this was a cacherequest node, and if we're here, we filled them
            #all out
            context = self.intermediates_[node]

            req = context.getCacheRequest()

            if CacheSemantics.isVectorCacheLoadRequest(req):
                with self.contextEnterer(context):
                    context.resetInterruptState()
                    context.resume(
                        ComputationResult_.Result(
                            ImplValContainer_(),
                            ImplValContainer_()
                            )
                        )
            elif CacheSemantics.isCacheRequestWithResult(req):
                result = CacheSemantics.getCacheRequestComputationResult(req)

                with self.contextEnterer(context):
                    context.resetInterruptState()
                    context.resume(result)
            else:
                cacheCalls = [x.extractApplyTuple() for x in CacheSemantics.processCacheCall(req)]

                res = []
                exception = None
                for t in cacheCalls:
                    assert t in self.finishedValues_, (
                        "Couldn't find result for: %s in %s" %
                            (t,"\n".join([str(x) for x in self.finishedValues_.keys()]))
                        )
                    if self.finishedValues_[t].isException():
                        if exception is None:
                            exception = self.finishedValues_[t]
                    else:
                        res.append(self.finishedValues_[t].asResult.result)

                with self.contextEnterer(context):
                    if exception:
                        context.resetInterruptState()
                        context.resume(exception)
                    else:
                        context.resetInterruptState()
                        context.resume(
                            ComputationResult_.Result(
                                ImplValContainer_(tuple(res)),
                                ImplValContainer_()
                                )
                            )
        else:
            #this was a split request
            splitResult, splitComputationLog = self.intermediates_[node]

            for slotComputation in splitResult.submittedComputations():
                assert slotComputation in self.finishedValues_

                value = self.finishedValues_[slotComputation]

                if value.isFailure():
                    self.finishNode_(node, value)
                    return
                else:
                    splitResult.futuresSplitResult.slotCompleted(
                        splitResult.computationsToSlotIndices[slotComputation],
                        value)
                    del splitResult.computationsToSlotIndices[slotComputation]

            submittableFutures = splitResult.futuresSplitResult.indicesOfSubmittableFutures()

            if len(submittableFutures) == 0:
                context = self.grabContext()

                toResumeWith = splitResult.futuresSplitResult.getFinalResult()
                context.resumePausedComputation(toResumeWith)
                context.resetInterruptState()
                self.intermediates_[node] = context
                with self.contextEnterer(context):
                    context.resume()

            else:
                with self.lock_:
                    futuresSplitResult = splitResult.futuresSplitResult

                    isFinished, result = self.findMeatyPausedComputations(futuresSplitResult)

                    if not isFinished:
                        splitResult = self.computeIntermediatesForSplitResult(
                            node, futuresSplitResult, result)

                        self.intermediates_[node] = (splitResult, [])

                        return

                    else:
                        toResume = result
                        context = self.grabContext()
                        context.resumePausedComputation(toResume)
                        context.resetInterruptState()
                        self.intermediates_[node] = context
                        with self.contextEnterer(context):
                            context.resume()

        while True:
            if context.isFinished():
                result = context.getFinishedResult()
                self.checkContextBackIn(context)

                #now, wake up any dependencies
                self.finishNode_(node, result)
                return

            elif context.isVectorLoad():
                for vectorToLoad in context.getVectorLoadAsVDIDs():
                    toLoad = None
                    loaded = False

                    if self.offlineCache_ is not None:
                        toLoad = self.offlineCache_.loadIfExists(vectorToLoad.page)
                        if toLoad is not None:
                            self.vdm_.loadSerializedVectorPage(vectorToLoad.page, toLoad)
                            loaded = True

                    if not loaded and vectorToLoad.isExternal():
                        #is this an external dataset, attempt to load it from there
                        PythonIoTasks.loadExternalDataset(
                            getCurrentS3Interface(),
                            vectorToLoad,
                            self.vdm_,
                            self.inProcessDownloader
                            )
                        loaded = True

                    assert loaded, "lost the definition for VDID: %s" % vectorToLoad

                with self.contextEnterer(context):
                    context.resetInterruptState()
                    context.resume()
                #go back around and try again

            elif context.isInterrupted():
                toResume = None
                if self.checkShouldSplit(context):
                    futuresSplitResult = context.splitWithFutures()

                    if futuresSplitResult is not None:
                        with self.lock_:
                            futuresSplitResult.disallowRepeatNodes()

                            isFinished, result = self.findMeatyPausedComputations(futuresSplitResult)

                            if not isFinished:
                                splitResult = self.computeIntermediatesForSplitResult(
                                    node, futuresSplitResult, result)

                                self.intermediates_[node] = (splitResult, context.getComputationLog())

                                self.checkContextBackIn(context)
                                return
                            else:
                                toResume = result

                #if we're here, then we didn't split
                #go back around and try again
                with self.contextEnterer(context):
                    if toResume is not None:
                        context.resumePausedComputation(toResume)
                    context.resetInterruptState()
                    context.resume()


            elif context.isCacheRequest():
                #these are thew new dependencies
                req = context.getCacheRequest()

                deps = set()

                if CacheSemantics.isVectorCacheLoadRequest(req):
                    pass
                elif CacheSemantics.isCacheRequestWithResult(req):
                    pass
                else:
                    cacheCalls = [x.extractApplyTuple() for x in CacheSemantics.processCacheCall(req)]

                    with self.lock_:
                        #register any dependencies
                        for t in cacheCalls:
                            if t not in self.finishedValues_ and t not in self.intermediates_:
                                #its a new request
                                self.intermediates_[t] = None
                                self.completable_.put(t)
                                self.watchers_[t] = threading.Event()
                            if t not in self.finishedValues_:
                                deps.add(t)
                        self.dependencies_[node] = deps

                if not deps:
                    #we could go again
                    with self.lock_:
                        self.completable_.put(node)
                return


callAndReturnExpr = FORANative.parseStringToExpression(
    """object {
    ...(f, *args) {
        try { (f`(*args), (f, *args), 'callAndReturnExpr') }
        catch from stacktrace (e) {  throw from stacktrace (e, (f, *args)) }
        }
    }""",
    FORANative.CodeDefinitionPoint(),
    "cdp"
    )

callAndReturn = FORANative.evaluateRootLevelCreateObjectExpression(callAndReturnExpr, {})

def areAllArgumentsConst(*args):
    """Returns True if all ImplValContainer arguments in the specified list are const."""
    for arg in args:
        if not arg.isCST():
            return False
    return True

class LocalEvaluator(EvaluatorBase.EvaluatorBase):
    def __init__(self,
                 offlineCacheFunction,
                 newMemLimit,
                 remoteEvaluator=None,
                 newLoadRatio=.5,
                 maxPageSizeInBytes=None,
                 vdmOverride=None):
        if maxPageSizeInBytes is None:
            maxPageSizeInBytes = Setup.config().maxPageSizeInBytes

        if vdmOverride is not None:
            self.vdm_ = vdmOverride
            self.offlineCache_ = None

        else:
            self.vdm_ = FORANative.VectorDataManager(
                CallbackSchedulerNative.createSimpleCallbackSchedulerFactory()
                    .createScheduler("LocalEvaluator", 1),
                maxPageSizeInBytes
                )

            self.vdm_.setDropUnreferencedPagesWhenFull(True)

            self.offlineCache_ = offlineCacheFunction(self.vdm_)

            if self.offlineCache_ is not None:
                self.vdm_.setOfflineCache(self.offlineCache_)

            logging.info("LocalEvaluator Creating VDMC with %s MB", newMemLimit / 1024.0 / 1024.0)

            self.vdm_.setMemoryLimit(newMemLimit, int(newMemLimit * 1.25))
            self.vdm_.setLoadRatio(newLoadRatio)

        self.remoteEvaluator_ = remoteEvaluator

        self.cache_ = ComputationCache(self.vdm_, self.offlineCache_)

    def flush(self):
        self.cache_.flush()

    def teardown(self):
        self.cache_.teardown()
        self.vdm_ = None
        self.offlineCache_ = None
        self.cache_ = None

    def getVDM(self):
        """return the current VectorDataManager"""
        return self.vdm_

    def evaluate(self, *args):
        argIv = FORANative.ImplValContainer(self.expandIfListOrTuple(callAndReturn, *args))
        res = self.evaluateDirectly(callAndReturn, *args)
        return FORANative.updateFreeStoreValues(argIv, res)

    def hasRemoteEvaluator(self):
        """Returns True if this LocalEvaluator has an inner RemoteEvaluator.

           A RemoteEvaluator is used to send all-const expressions for evaluation
           in a remote cluster.
        """
        return self.remoteEvaluator_ is not None

    def evaluateEntirelyLocally(self, *args):
        return self.cache_.cacheLookupSeveral([args], leaveInCache = False)[0]

    def evaluateDirectly(self, *args):
        """evaluates an apply of ImplValContainer objects entirely in local memory."""
        args = self.expandIfListOrTuple(*args)
        #at this point, args is the list of things to compute

        if self.hasRemoteEvaluator() and areAllArgumentsConst(*args):
            return self.remoteEvaluator_.evaluate(*args)


        return self.cache_.cacheLookupSeveral([args], leaveInCache = False)[0]


def defaultLocalEvaluator(remoteEvaluator=None, vdmOverride=None):
    return LocalEvaluator(
        lambda vdm: None,
        Setup.config().cumulusVectorRamCacheMB * 1024 * 1024,
        remoteEvaluator,
        vdmOverride=vdmOverride
        )


