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
    def __init__(self, node, splits, childComputations, context):
        self.node = node
        self.splits = splits
        self.context = context
        self.childComputations = childComputations

class SplitSubcomputation(object):
    def __init__(self, pausedComputationTree):
        self.pausedComputationTree = pausedComputationTree

def getCurrentS3Interface():
    return ActualS3Interface.ActualS3InterfaceFactory()

class ComputationCache(Stoppable.Stoppable):
    def __init__(self, vdm, offlineCache):
        Stoppable.Stoppable.__init__(self)
        self.dependencies_ = TwoWaySetMap.TwoWaySetMap()
        self.vdm_ = vdm
        self.offlineCache_ = offlineCache
        self.finishedValuesAndTimeElapsed_ = {}
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
        self.finishedValuesAndTimeElapsed_ = {}
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
        self.finishedValuesAndTimeElapsed_ = {}
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
                    if comp not in self.finishedValuesAndTimeElapsed_ and comp not in self.intermediates_
                ]

            for comp in computationsToCall:
                #put it in the cache if its not there already
                if comp not in self.finishedValuesAndTimeElapsed_ and comp not in self.intermediates_:
                    self.intermediates_[comp] = None
                    self.completable_.put(comp)
                    self.watchers_[comp] = threading.Event()

            allDone = True
            for comp in computationsToCall:
                if comp not in self.finishedValuesAndTimeElapsed_:
                    allDone = False

        #wait until the event is set. at this point the value should
        #be filled out
        if not allDone and block:
            for comp in computationsToCall:
                self.watchers_[comp].wait()
            allDone = True

        if allDone:
            result = [self.finishedValuesAndTimeElapsed_[comp][0] for comp in computationsToCall]

            if not leaveInCache:
                for c in notAlreadyInCache:
                    del self.finishedValuesAndTimeElapsed_[c]

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
                                        self.finishNode_(
                                            l,
                                            ComputationResult_.Exception(
                                                ImplValContainer_(
                                                    ("cyclic cachecall detected",
                                                        FORANative.emptyStackTrace
                                                        )
                                                    ),
                                                ImplValContainer_()
                                                ),
                                            FORANative.TimeElapsed()
                                            )
                                    curNode = None
                                else:
                                    curNodeSet.add(curNode)
                                    curNodeList.append(curNode)

                    for x in self.computingContexts_:
                        try:
                            if ((time.time() - self.computingContexts_t0_[x]) >
                                                kMinSplitTimeInterval and not DISABLE_SPLITTING):
                                self.isSplit_.add(x)
                                self.computingContexts_[x].interrupt()
                                self.computingContexts_t0_[x] = time.time()
                        except:
                            traceback.print_exc()
            except:
                traceback.print_exc()

    def timeElapsedForContext(self, c):
        te = c.getTotalTimeElapsed()
        return te.timeSpentInInterpreter + te.timeSpentInCompiledCode

    def finishNode_(self, node, result, timeElapsed):
        with self.lock_:
            self.finishedValuesAndTimeElapsed_[node] = (result, timeElapsed)
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

    def computeIntermediatesForSplitResult(self, node, splits, context):
        deps = set()

        childComputations = []

        for split in splits:
            pausedComputation = split.childComputation

            child = SplitSubcomputation(pausedComputation)

            self.intermediates_[child] = None
            self.completable_.put(child)
            self.watchers_[child] = threading.Event()
            deps.add(child)
            childComputations.append(child)

        self.dependencies_[node] = deps

        return SplitResult(node, splits, childComputations, context)

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
                        context.placeInEvaluationStateWithoutRenamingMutableVectors(
                            ImplValContainer_(tuple(node))
                            )
                    context.compute()

                elif isinstance(node, SplitSubcomputation):
                    context.resumePausedComputation(node.pausedComputationTree)
                    context.resetInterruptState()
                    context.compute()
                else:
                    assert False, "don't know what to do with node of type %s" % node

            self.intermediates_[node] = context

        elif isinstance(self.intermediates_[node], FORANative.ExecutionContext):
            #this was a cacherequest node, and if we're here, we filled them
            #all out
            context = self.intermediates_[node]

            req = context.getCacheRequest()

            if CacheSemantics.isCacheRequestWithResult(req):
                result = CacheSemantics.getCacheRequestComputationResult(req)

                with self.contextEnterer(context):
                    context.resetInterruptState()
                    context.addCachecallResult(result)
                    context.compute()
            else:
                cacheCalls = [x.extractApplyTuple() for x in CacheSemantics.processCacheCall(req)]

                res = []
                exception = None
                for t in cacheCalls:
                    assert t in self.finishedValuesAndTimeElapsed_, (
                        "Couldn't find result for: %s in %s" %
                            (t,"\n".join([str(x) for x in self.finishedValuesAndTimeElapsed_.keys()]))
                        )
                    if self.finishedValuesAndTimeElapsed_[t][0].isException():
                        if exception is None:
                            exception = self.finishedValuesAndTimeElapsed_[t][0]
                    else:
                        res.append(self.finishedValuesAndTimeElapsed_[t][0].asResult.result)

                with self.contextEnterer(context):
                    if exception:
                        context.resetInterruptState()
                        context.addCachecallResult(exception)
                        context.compute()
                    else:
                        context.resetInterruptState()
                        context.addCachecallResult(
                            ComputationResult_.Result(
                                ImplValContainer_(tuple(res)),
                                ImplValContainer_()
                                )
                            )
                        context.compute()
        else:
            #this was a split request
            splitResult = self.intermediates_[node]

            for ix in range(len(splitResult.splits)):
                child = splitResult.childComputations[ix]

                assert child in self.finishedValuesAndTimeElapsed_

                value = self.finishedValuesAndTimeElapsed_[child][0]
                timeElapsed = self.finishedValuesAndTimeElapsed_[child][1]
                del self.finishedValuesAndTimeElapsed_[child]

                if value.isFailure():
                    self.finishNode_(node, value)
                    self.checkContextBackIn(splitResult.context)
                    return
                else:
                    splitResult.context.absorbSplitResult(
                        splitResult.splits[ix].computationHash, 
                        value,
                        timeElapsed
                        )

            with self.lock_:
                context = splitResult.context
                context.resetInterruptState()
                self.intermediates_[node] = context
                with self.contextEnterer(context):
                    context.compute()

        while True:
            if context.isFinished():
                result = context.getFinishedResult()
                timeElapsed = context.getTotalTimeElapsed()

                self.checkContextBackIn(context)

                #now, wake up any dependencies
                self.finishNode_(node, result, timeElapsed)
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
                    context.compute()
                #go back around and try again

            elif context.isInterrupted():
                toResume = None
                if self.checkShouldSplit(context):
                    splits = context.splitComputation()

                    if splits is not None:
                        with self.lock_:
                            splitResult = self.computeIntermediatesForSplitResult(node, splits, context)
                            self.intermediates_[node] = splitResult
                            return

                #if we're here, then we didn't split
                #go back around and try again
                with self.contextEnterer(context):
                    if toResume is not None:
                        context.resumePausedComputation(toResume)
                    context.resetInterruptState()
                    context.compute()
                    

            elif context.isCacheRequest():
                #these are thew new dependencies
                req = context.getCacheRequest()

                deps = set()

                if CacheSemantics.isCacheRequestWithResult(req):
                    pass
                else:
                    cacheCalls = [x.extractApplyTuple() for x in CacheSemantics.processCacheCall(req)]

                    with self.lock_:
                        #register any dependencies
                        for t in cacheCalls:
                            if t not in self.finishedValuesAndTimeElapsed_ and t not in self.intermediates_:
                                #its a new request
                                self.intermediates_[t] = None
                                self.completable_.put(t)
                                self.watchers_[t] = threading.Event()
                            if t not in self.finishedValuesAndTimeElapsed_:
                                deps.add(t)
                        self.dependencies_[node] = deps

                if not deps:
                    #we could go again
                    with self.lock_:
                        self.completable_.put(node)
                return


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
                    remoteEvaluator = None,
                    newLoadRatio = .5,
                    maxPageSizeInBytes = None,
                    vdmOverride = None
                    ):
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

        self.cache_ = ComputationCache(
                self.vdm_,
                self.offlineCache_,
                )

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
        return self.evaluateDirectly(args[0], *args[1:])

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

        if (self.hasRemoteEvaluator() and self.areAllArgumentsConst(*args)):
            return self.remoteEvaluator_.evaluate(*args)


        return self.cache_.cacheLookupSeveral([args], leaveInCache = False)[0]


def defaultLocalEvaluator(remoteEvaluator=None, vdmOverride=None):
    return LocalEvaluator(
        lambda vdm: None,
        Setup.config().cumulusVectorRamCacheMB * 1024 * 1024,
        remoteEvaluator,
        vdmOverride=vdmOverride
        )


