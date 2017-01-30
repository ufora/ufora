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

import unittest
import threading
import time
import random
import re
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.FORA as FORANative
import ufora.config.Setup as Setup
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

def triggerAfter(f, timeout):
    """call 'f' after timeout seconds"""
    def threadFun():
        time.sleep(timeout)
        f()
    threading.Thread(target = threadFun).start()

def enum(**enums):
    return type('Enum', (), enums)

def evaluate(context, *args):
    context.placeInEvaluationState(FORANative.ImplValContainer(args))
    context.compute()

#ExecutionMode = enum(Interpreted=0, SampledSpecializations=1, Compiled=2)
#InterruptAction = enum(Noop=0, SpecializeOnCurrent=1, DrainAllPendingCompilations=2)

def dumpToFile(toDump, fileName):
    with open(fileName, "w") as f:
        for item in toDump:
            print >> f, str(item)

class TestExecutionContext(unittest.TestCase):
    def setUp(self):
        self.executionContextSeed = random.randint(0, 4294967295)
        self.interruptRate = 1000

        #Runtime.getMainRuntime().dynamicOptimizer.clearInstructionCache()
        #Runtime.getMainRuntime().dynamicOptimizer.resume()

        self.loopFun = FORA.extractImplValContainer(
            FORA.eval(
                """fun()
                    {
                    let c = 0;
                    while (true)
                        c = c + 1;
                    }
                """))

        self.simpleSum = FORA.extractImplValContainer(
            FORA.eval(
                """fun ()
                    {
                    let sum = fun(a, b)
                        {
                        if (a >= b)
                            return nothing
                        if (a+1 >= b)
                            return a

                        let mid = Int64((a+b)/2);
                        return sum(a, mid) + sum(mid, b)
                        }
                    return sum(0, 2000)
                    }
                """))

        self.simpleLoop = FORA.extractImplValContainer(
            FORA.eval("""fun() { let x = 0; while (x < 10000) x = x + 1; return x }""")
            )

    # TODO: reenable these tests with the new compiler model
    # def test_deterministicInterrupt(self):
    #     self.verifyDeterministicExecutionWithSpecializations(self.simpleLoop)

    # def test_deterministicInterrupt_in_loop(self):
    #     self.verifyDeterministicExecutionInInterpreter(self.simpleLoop)

    # def test_deterministicExecution_of_sum_interpreted(self):
    #     self.verifyDeterministicExecutionInInterpreter(self.simpleSum)

    # def test_deterministicExecution_of_sum_with_specializations(self):
    #     self.verifyDeterministicExecutionWithSpecializations(self.simpleSum)

    # def test_deterministicExecution_of_sum_compiled(self):
    #     self.verifyDeterministicExecutionInCompiler(self.simpleSum)

    # def verifyDeterministicExecutionInInterpreter(self, fun):
    #     return self.verifyDeterministicExecution(fun, ExecutionMode.Interpreted)

    # def verifyDeterministicExecutionWithSpecializations(self, fun):
    #     return self.verifyDeterministicExecution(fun, ExecutionMode.SampledSpecializations)

    # def verifyDeterministicExecutionInCompiler(self, fun):
    #     return self.verifyDeterministicExecution(fun, ExecutionMode.Compiled)

    # def verifyDeterministicExecution(self, fun, executionMode=ExecutionMode.Compiled):

    #     firstPassResults = None

    #     runFirst = None
    #     runRest = None
    #     if executionMode == ExecutionMode.SampledSpecializations:
    #         runFirst = runRest = self.runWithSpecializations
    #         runFirst(fun)
    #     elif executionMode == ExecutionMode.Interpreted:
    #         runFirst = runRest = self.runInterpreted
    #     elif executionMode == ExecutionMode.Compiled:
    #         #self.runCompiled(fun)
    #         runFirst = self.runCompiled
    #         runRest = self.runInterpreted
    #     else:
    #         self.assertEqual(executionMode, ExecutionMode.Compiled)

    #     for passIndex in range(4):
    #         Runtime.getMainRuntime().dynamicOptimizer.clearInstructionCache()
    #         print "Starting pass", passIndex

    #         rawTrace, steps1 = runFirst(fun)
    #         newTrace = "\n".join(rawTrace)
    #         self.assertTrue(len(steps1) > 0)

    #         rawTrace, steps2 = runRest(fun)
    #         newTrace2 = "\n".join(rawTrace)
    #         self.assertTrue(len(steps2) > 0)

    #         rawTrace, steps3 = runRest(fun, steps2)
    #         newTrace3 = "\n".join(rawTrace)
    #         self.assertTrue(len(steps3) > 0)

    #         if executionMode == ExecutionMode.Interpreted:
    #             self.compareLists(steps1, steps2, 'inner1')
    #         self.compareLists(steps2, steps3, 'inner2')

    #         if passIndex == 0:
    #             # we compare traces to the ones from the second iteration because
    #             # the first iteration can have interpreter frames that don't appear
    #             # in subsequent runs once code has been compiled.
    #             firstPassResults = {}
    #             firstPassResults["steps1"] = steps1
    #             firstPassResults["steps2"] = steps2
    #             firstPassResults["steps3"] = steps3
    #         elif passIndex > 0:
    #             self.compareLists(firstPassResults["steps1"], steps1, 'diff1')
    #             self.compareLists(firstPassResults["steps2"], steps2, 'diff2')
    #             self.compareLists(firstPassResults["steps3"], steps3, 'diff3')

    # def runWithInterrupts(self, func, interruptAction, previousTrace):
    #     vdm = FORANative.VectorDataManager(Setup.config().maxPageSizeInBytes)
    #     if interruptAction == InterruptAction.DrainAllPendingCompilations:
    #         context = ExecutionContext.ExecutionContext(dataManager = vdm)
    #         Runtime.getMainRuntime().dynamicOptimizer.pause()
    #     else:
    #         context = ExecutionContext.ExecutionContext(
    #             dataManager = vdm,
    #             allowInterpreterTracing = False
    #             )

    #     context.enalbeExecutionStepsRecording()
    #     if previousTrace != None:
    #         context.setExpectedSteps(previousTrace)
    #     context.interruptAfterCycleCount(self.interruptRate)
    #     evaluate(context, func, FORANative.symbol_Call)

    #     traces = []
    #     while context.isInterrupted():
    #         Runtime.getMainRuntime().dynamicOptimizer.resume()
    #         Runtime.getMainRuntime().dynamicOptimizer.drainCompilationQueue()
    #         Runtime.getMainRuntime().dynamicOptimizer.pause()

    #         traces.append(context.extractCurrentTextStacktrace())

    #         if interruptAction == InterruptAction.SpecializeOnCurrent:
    #             context.specializeOnCurrentInterpreterInstruction()

    #         context.resetInterruptState()
    #         context.interruptAfterCycleCount(self.interruptRate)
    #         context.resume()

    #     self.assertTrue(context.isFinished())
    #     return ([re.sub("CIG_[0-9]+", "CIG", x) for x in traces], context.getRecordedSteps())

    # def runWithSpecializations(self, func, previousTrace=None):
    #     return self.runWithInterrupts(func, InterruptAction.SpecializeOnCurrent, previousTrace)

    # def runInterpreted(self, func, previousTrace=None):
    #     return self.runWithInterrupts(func, InterruptAction.Noop, previousTrace)

    # def runCompiled(self, func, previousTrace=None):
    #     return self.runWithInterrupts(func, InterruptAction.DrainAllPendingCompilations, previousTrace)

    def compareLists(self, list1, list2, prefix):
        l1 = [(i[0], i[1]) for i in list1]
        l2 = [(i[0], i[1]) for i in list2]
        if len(l1) != len(l2) or  l1 != l2:
            dumpToFile(list1, prefix + ".1")
            dumpToFile(list2, prefix + ".2")
            self.assertTrue(False, "lists differ. prefix= " + prefix)

    def test_refcountsInCompiledCode(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = True,
            blockUntilTracesAreCompiled = True,
            allowInternalSplitting = False
            )

        text = """fun(){
        let f = fun(v, depth) {
            if (depth > 100)
                //this will trigger an interrupt since the data cannot exist in the VDM
                datasets.s3('','')
            else
                f(v, depth+1)
            }

        f([1,2,3,4,5], 0)
        }"""

        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval(text)),
            FORANative.symbol_Call
            )

        stacktraceText = context.extractCurrentTextStacktrace()

        self.assertTrue(stacktraceText.count("Vector") < 10)

    def pageLargeVectorHandlesTest(self, text, cycleCount, expectsToHavePages):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        context.configuration.agressivelyValidateRefcountsAndPageReachability = True

        context.placeInEvaluationState(
                FORANative.ImplValContainer(
                    (
                    FORA.extractImplValContainer(FORA.eval(text)),
                    FORANative.symbol_Call
                    )
                )
            )
        context.interruptAfterCycleCount(cycleCount)

        context.compute()

        if expectsToHavePages:
            self.assertTrue(context.pageLargeVectorHandles(0))
            self.assertFalse(context.pageLargeVectorHandles(0))
        else:
            self.assertFalse(context.pageLargeVectorHandles(0))

        return context

    def test_pageLargeVectorHandleSlicesWorks(self):
        context = self.pageLargeVectorHandlesTest("""fun() {
                        let v = Vector.range(100);
                        v = v + v + v + v
                        v = v + v + v + v
                        let v2 = v[10,-10];

                        let res = 0;
                        for ix in sequence(10000) {
                            res = res + v[0]
                            }

                        size(v2)
                        }""",
                    5000,
                    True
                    )

        context.resetInterruptState()
        context.compute()

        self.assertEqual(context.getFinishedResult().asResult.result.pyval, 1580)

    def test_pageLargeVectorHandles(self):
        #check that walking a frame with a few VectorHandles works
        self.pageLargeVectorHandlesTest(
                    """fun() {
                        let res = 0
                        let v = [1,2,3];
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v

                        for ix in sequence(10000)
                            res = res + ix

                        res + v[0]
                        }""",
                    5000,
                    True
                    )

    def test_pageLargeVectorHandles_2(self):
        #check that walking a frame with a few VectorHandles works
        self.pageLargeVectorHandlesTest(
                    """fun() {
                        let res = 0
                        let v = [1,2,3];
                        let v2 = [v,v,v,v,v,v]

                        for ix in sequence(10000)
                            res = res + ix

                        res + v2[0][0]
                        }""",
                    5000,
                    True
                    )

    def test_pageLargeVectorHandles_3(self):
        #check that walking a frame with a few VectorHandles works
        self.pageLargeVectorHandlesTest(
                    """fun() {
                        let res = 0
                        let v = [[x for x in sequence(ix)] for ix in sequence(1000)]

                        v.sum(fun(x){x.sum()})
                        }""",
                    300000,
                    True
                    )

    def test_pageLargeVectorHandles_4(self):
        #check that walking a frame with a few VectorHandles works
        self.pageLargeVectorHandlesTest(
                    """fun() {
                        let res = 0
                        let v = [1,2,3,4]
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v

                        let f = fun(vec, x) {
                            if (x > 0)
                                return f(vec, x - 1) + f(vec, x - 1)
                            else
                                return 0
                            }

                        f(v, 10)
                        }""",
                    1000,
                    True
                    )

    def test_pageLargeVectorHandles_5(self):
        #check that walking a frame with a few VectorHandles works
        self.pageLargeVectorHandlesTest(
                    """fun() {
                        let res = 0
                        let v = [1,2,3,4]
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v
                        v = v + v + v + v

                        let f = fun(vec) {
                            let res = 0;
                            for ix in sequence(1, size(vec) - 1)
                                res = res + f(vec[,ix]) + f(vec[ix,])
                            res
                            }

                        f(v)
                        }""",
                    10000,
                    True
                    )


    def test_resumingAfterCopyDataOutOfPages(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInternalSplitting = False
            )

        text = """
        fun() {
            let v = Vector.range(1000).paged;

            let ix1 = 0
            let res = 0
            while (true) {
                res = res + v[ix1]
                ix1 = (ix1 + 1) % size(v)
                }
            res
            }"""

        context.placeInEvaluationState(FORANative.ImplValContainer((
            FORA.extractImplValContainer(FORA.eval(text)),
            FORANative.symbol_Call
            )))
        context.interruptAfterCycleCount(100000)

        context.compute()

        paused1 = context.extractPausedComputation()

        while not context.isVectorLoad():
            context.copyValuesOutOfVectorPages()
            vdm.unloadAllPossible()
            context.resetInterruptState()
            context.interruptAfterCycleCount(100000)
            context.compute()

        paused2 = context.extractPausedComputation()

        self.assertTrue(len(paused1.asThread.computation.frames) == len(paused2.asThread.computation.frames))
            
    def copyDataOutOfPagesTest(self, text, cycleCount, expectsToHaveCopies):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        context.configuration.agressivelyValidateRefcountsAndPageReachability = True
        context.configuration.releaseVectorHandlesImmediatelyAfterExecution = False

        context.placeInEvaluationState(FORANative.ImplValContainer((
            FORA.extractImplValContainer(FORA.eval(text)),
            FORANative.symbol_Call
            )))
        
        context.interruptAfterCycleCount(cycleCount)

        context.compute()

        if expectsToHaveCopies:
            self.assertTrue(context.copyValuesOutOfVectorPages())
            self.assertFalse(context.copyValuesOutOfVectorPages())
        else:
            self.assertFalse(context.copyValuesOutOfVectorPages())

    def test_copyDataOutOfPages_1(self):
        #verify that just walking the stackframes doesn't segfault us
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0
                        for ix in sequence(10000)
                            res = res + ix
                        res
                        }""",
                    5000,
                    False
                    )

    def test_copyDataOutOfPages_2(self):
        #check that walking a frame with a VectorHandle appears to work
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0
                        let v = [1,2,3].paged;

                        for ix in sequence(10000)
                            res = res + ix

                        res + v[0]
                        }""",
                    5000,
                    False
                    )

    def test_copyDataOutOfPages_3(self):
        #walk a frame where we are holding a VectorHandle from within a paged vector
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0

                        //allocate a vector that's a reference into a paged Vector
                        let v = [[1,2,3]].paged[0];

                        for ix in sequence(10000)
                            res = res + ix

                        res + v[0]
                        }""",
                    5000,
                    True
                    )



    def test_copyDataOutOfPages_4(self):
        #walk a frame where we are holding a VectorHandle from within a paged vector
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0

                        //allocate one vector, but put it in twice, and pull it out twice
                        let (v1, v2) = (
                            let v0 = [1,2,3]
                            let vPaged = [v0,v0].paged;
                            (vPaged[0],vPaged[1])
                            );

                        for ix in sequence(10000)
                            res = res + ix

                        res + v1[0] + v2[0]
                        }""",
                    5000,
                    True
                    )



    def test_copyDataOutOfPages_5(self):
        #walk a frame where we are holding a VectorHandle from within a paged vector
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0

                        let v = [ [ [1.0].paged ] ].paged;

                        //now grab interior vector
                        let v2 = v[0]

                        for ix in sequence(10000)
                            res = res + ix

                        res + size(v2)
                        }""",
                    5000,
                    True
                    )

    def test_copyDataOutOfPages_Strings(self):
        #walk a frame where we are holding a VectorHandle from within a paged vector
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0

                        //allocate one vector, but put it in twice, and pull it out twice
                        let (a, b) = (
                            let v = ["asdfasdfasdfasdfasdfasdfasdfasdfasdfasdf",
                                "bsdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf",
                                "casasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfdfasdfasdf"].paged;
                            (v[0],v[1])
                            );

                        for ix in sequence(10000)
                            res = res + ix

                        res + a[0] + b[0]
                        }""",
                    5000,
                    True
                    )

    def test_copyDataOutOfPages_VectorTrees(self):
        #walk a frame where we are holding a VectorHandle from within a paged vector
        self.copyDataOutOfPagesTest(
                    """fun() {
                        let res = 0

                        //allocate one vector, but put it in twice, and pull it out twice
                        let (v1, v2) = (
                            let v0 = ["a"].paged + ["b"] + ["c"].paged + ["d"] + ["e"].paged;
                            let vPaged = [v0,v0].paged;
                            (vPaged[0],vPaged[1])
                            );

                        for ix in sequence(10000)
                            res = res + ix

                        res + v1[0] + v2[0]
                        }""",
                    5000,
                    True
                    )

    def test_verifyThatExtractingPausedComputationsDoesntDuplicateLargeStrings(self):
        text = """fun() {
            let s = ' '
            while (size(s) < 1000000)
                s = s + s

            let f = fun(x) { if (x > 0) return f(x-1) + s[x]; `TriggerInterruptForTesting() }

            f(20)
            }"""

        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        
        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )
        
        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval(text)),
            FORANative.symbol_Call
            )

        computation = context.extractPausedComputation()

        context2 = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        context2.resumePausedComputation(computation)
        
        self.assertTrue(
            context2.totalBytesUsed < 2 * context.totalBytesUsed
            )


    def test_extractPausedComputation(self):
        text = """fun() {
            let x = 0;
            while (x < 100000)
                x = x + 1
            x
            }"""

        self.runtime = Runtime.getMainRuntime()
        #self.dynamicOptimizer = self.runtime.dynamicOptimizer

        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )
        
        context.interruptAfterCycleCount(1010)

        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval(text)),
            FORANative.symbol_Call
            )

        computation = context.extractPausedComputation()
        
        context2 = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        context2.resumePausedComputation(computation)
        context2.compute()

        self.assertEqual(context2.getFinishedResult().asResult.result.pyval, 100000)

        context.teardown()
        context2.teardown()

    def test_extractPausedComputationDuringVectorLoad(self):
        self.runtime = Runtime.getMainRuntime()
        #self.dynamicOptimizer = self.runtime.dynamicOptimizer

        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval("fun() { [1,2,3].paged }")),
            FORANative.ImplValContainer(FORANative.makeSymbol("Call"))
            )

        pagedVec = context.getFinishedResult().asResult.result
        
        vdm.unloadAllPossible()

        context.placeInEvaluationState(
            FORANative.ImplValContainer(
                (pagedVec,
                FORANative.ImplValContainer(FORANative.makeSymbol("GetItem")),
                FORANative.ImplValContainer(0))
                )
            )

        context.compute()

        self.assertTrue(context.isVectorLoad(), context.extractCurrentTextStacktrace())

        computation = context.extractPausedComputation()

        self.assertEqual(len(computation.asThread.computation.frames),1)

    def test_resumePausedComputationWithResult(self):
        self.runtime = Runtime.getMainRuntime()
        #self.dynamicOptimizer = self.runtime.dynamicOptimizer

        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)

        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInterpreterTracing = False,
            allowInternalSplitting = False
            )

        text = """
        let f = fun(v, ix) {
            if (ix > 0)
                {
                let (v2,res) = f(v,ix-1);
                return (v2, res + v2[0])
                }

            `TriggerInterruptForTesting()

            return (v, 0)
            };

        f([1], 10)
        """

        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval("fun() { " + text + " }")),
            FORANative.ImplValContainer(FORANative.makeSymbol("Call"))
            )

        assert context.isInterrupted()

        pausedComp = context.extractPausedComputation()

        framesToUse = pausedComp.asThread.computation.frames[0:5]

        pausedComp2 = FORANative.PausedComputationTree(
            FORANative.PausedComputation(
                framesToUse,
                FORA.extractImplValContainer(FORA.eval("([2], 0)", keepAsForaValue=True)),
                False
                )
            )

        context.resumePausedComputation(pausedComp2)

        context.copyValuesOutOfVectorPages()
        context.pageLargeVectorHandles(0)

        context.resetInterruptState()
        context.compute()

        self.assertTrue( context.isFinished() )

        result = context.getFinishedResult()

        self.assertTrue(result.asResult.result[1].pyval == 6)


    def test_interrupt_works(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(dataManager = vdm, allowInternalSplitting = False)

        triggerAfter(context.interrupt, .03)

        t0 = time.time()

        evaluate(context, self.loopFun, FORANative.symbol_Call)
        #make sure we actually looped!
        self.assertTrue(time.time() - t0 > .02)

        self.assertFalse(context.isEmpty())
        self.assertFalse(context.isCacheRequest())
        self.assertFalse(context.isVectorLoad())
        self.assertFalse(context.isFinished())
        self.assertTrue(context.isInterrupted())


    def test_serialize_while_holding_interior_vector(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(dataManager = vdm, allowInterpreterTracing=False, allowInternalSplitting=False)

        evaluate(context, 
            FORA.extractImplValContainer(
                FORA.eval("""
                    fun() {
                        let v = [[1].paged].paged; 
                        let v2 = v[0]

                        `TriggerInterruptForTesting()

                        1+2+3+v+v2
                        }"""
                    )
                ),
            FORANative.symbol_Call
            )

        self.assertTrue(context.isInterrupted())

        serialized = context.serialize()

        context = None



    def test_serialize_during_vector_load(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(dataManager = vdm, allowInternalSplitting=False)

        evaluate(context, 
            FORA.extractImplValContainer(
                FORA.eval("fun(){ datasets.s3('a','b')[0] }")
                ),
            FORANative.symbol_Call
            )

        self.assertTrue(context.isVectorLoad())

        serialized = context.serialize()

        context2 = ExecutionContext.ExecutionContext(dataManager = vdm, allowInternalSplitting=False)
        context2.deserialize(serialized)

        self.assertTrue(context2.isVectorLoad())


    def test_teardown_during_vector_load(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInternalSplitting = False
            )

        evaluate(context, 
                FORA.extractImplValContainer(
                    FORA.eval("fun() { let v = [1,2,3].paged; fun() { v[1] } }")
                    ),
                FORANative.symbol_Call
                )
        vdm.unloadAllPossible()

        pagedVecAccessFun = context.getFinishedResult().asResult.result

        context.teardown()

        evaluate(context, 
            pagedVecAccessFun,
            FORANative.symbol_Call
            )

        self.assertFalse(context.isInterrupted())
        self.assertTrue(context.isVectorLoad())

        context.teardown()

    def extractPagedUnloadedVector(self, vdm, count):
        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInternalSplitting = False
            )

        evaluate(context, 
            FORA.extractImplValContainer(FORA.eval("fun() { Vector.range(%s).paged }" % count)),
            FORANative.ImplValContainer(FORANative.makeSymbol("Call"))
            )

        pagedVec = context.getFinishedResult().asResult.result
        
        vdm.unloadAllPossible()

        return pagedVec

    def test_teardown_simple(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(dataManager = vdm, allowInternalSplitting=False)

        evaluate(context, 
            FORA.extractImplValContainer(
                FORA.eval("fun(){nothing}")
                ),
            FORANative.symbol_Call
            )

        context.getFinishedResult()

        toEval = FORA.extractImplValContainer(
            FORA.eval(
                """fun() {
                    let f = fun() { };
                    let v = [1, [3]];
                    cached(f())
                    }"""
                )
            )

        evaluate(context, toEval, FORANative.symbol_Call)

        while not context.isCacheRequest():
            context.compute()

        context.teardown(True)


    def test_teardown_simple_2(self):
        vdm = FORANative.VectorDataManager(callbackScheduler, Setup.config().maxPageSizeInBytes)
        context = ExecutionContext.ExecutionContext(
            dataManager = vdm,
            allowInternalSplitting = False
            )

        context.placeInEvaluationState(FORANative.ImplValContainer((
            FORA.extractImplValContainer(
                FORA.eval("fun(){ let f = fun() { throw 1 }; try { f() } catch(...) { throw 2 } }")
                ),
            FORANative.symbol_Call
            )))

        context.compute()
        self.assertTrue(context.getFinishedResult().isException())

    def stringAllocShouldFailFun(self, ct):
        return FORA.extractImplValContainer(
            FORA.eval(
                """fun()
                    {
                    let s = "*";
                    let i = 0;
                    while (i < 100000)
                        {
                        s = s + "%s" + s + "%s";
                        i = i + 1;
                        }
                    }
                """ % (" ", " " * ct)))

    def test_large_string_alloc_fails_and_raises_foravalue_error(self):
        for ix in range(10):
            val = ForaValue.FORAValue(self.stringAllocShouldFailFun(ix))
            self.assertRaises(ForaValue.FORAFailure, val)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([ExecutionContext, Evaluator])
