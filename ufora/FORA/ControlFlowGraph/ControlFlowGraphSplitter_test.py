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
import logging

import ufora.native.FORA as ForaNative
import ufora.FORA.python.ExecutionContext as ExecutionContext

import ufora.FORA.python.FORA as FORA
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()
callbackSchedulerFactory = callbackScheduler.getFactory()

emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])

class NotInterruptedException(Exception):
    def __init__(self, context):
        self.context = context
    def __repr__(self):
        return repr(self.context)

class NotAResultException(Exception):
    def __init__(self, x):
        self.val = x
    def __repr__(self):
        return repr(self.val)

class CouldntFinishException(Exception):
    def __init__(self, x):
        self.val = x
    def __repr__(self):
        return repr(self.val)

def finishPausedComputation(pausedComputation):
    vdm = ForaNative.VectorDataManager(callbackScheduler, 50 * 1024 * 1024)

    context2 = ExecutionContext.ExecutionContext(
        dataManager = vdm,
        allowInterpreterTracing = False
        )

    context2.resumePausedComputation(pausedComputation)
    context2.resume()

    if (not context2.isFinished()):
        raise CouldntFinishException(pausedComputation)

    finishedResult = context2.getFinishedResult()

    if (finishedResult.isResult()):
        return finishedResult.asResult.result
    elif (finishedResult.isException()):
        return finishedResult.asException.exception
    else:
        raise Exception("computation failed")

def callAndGetResult(funImplVal):
    vdm = ForaNative.VectorDataManager(callbackScheduler, 50 * 1024 * 1024)

    context = ExecutionContext.ExecutionContext(
        dataManager = vdm,
        allowInterpreterTracing = False
        )

    context.evaluate(funImplVal, ForaNative.symbol_Call)

    finishedResult = context.getFinishedResult()

    if (not finishedResult.isResult()):
        raise NotAResultException(finishedResult)

    return finishedResult.asResult.result

def callAndExtractPausedCompuationAfterSteps(funToCall, steps):
    vdm = ForaNative.VectorDataManager(callbackScheduler, 50 * 1024 * 1024)

    context = ExecutionContext.ExecutionContext(
        dataManager = vdm,
        allowInterpreterTracing = False
        )

    context.interruptAfterCycleCount(steps)

    context.evaluate(
        funToCall,
        ForaNative.symbol_Call
        )

    if (not context.isInterrupted()):
        raise NotInterruptedException(context)

    computation = context.extractPausedComputation()
    context.teardown()

    return computation

class ControlFlowGraphSplitterTest(unittest.TestCase):
    def parseStringToFunction(self, expr):
        expression = ForaNative.parseStringToExpression(expr, emptyCodeDefinitionPoint, "")
        return expression.extractRootLevelCreateFunctionPredicate()

    def test_cfgSplitting_1(self):
        cfg1 = self.parseStringToFunction("fun(f) { f(1) + f(1+3) }").toCFG(1)

        steps = ForaNative.extractApplyStepsFromControlFlowGraph(cfg1, "block_0Let")
        self.assertEqual(len(steps), 4)

        splits = ForaNative.splitControlFlowGraph(cfg1, "block_0Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_2(self):
        cfg1 = self.parseStringToFunction("fun(f) { f(f(1)) }").toCFG(1)

        splits = ForaNative.splitControlFlowGraph(cfg1, None)

        self.assertTrue(splits is None)

    def test_cfgSplitting_3(self):
        cfg1 = self.parseStringToFunction("fun(f) { 1 }").toCFG(1)

        splits = ForaNative.splitControlFlowGraph(cfg1, None)

        self.assertTrue(splits is None)

    def test_cfgSplitting_4(self):
        funString = "fun(f) { f(1) + (f(2) * f(3)) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        steps = ForaNative.extractApplyStepsFromControlFlowGraph(cfg, None)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_0Let")
        self.assertTrue(splits is not None)

    def test_cfgSplitting_5(self):
        funString = "fun(f) { (f(1) + f(2)) + f(3) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        steps = ForaNative.extractApplyStepsFromControlFlowGraph(cfg, None)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_0Let")
        self.assertTrue(splits is not None)

    def test_cfgSplitting_6(self):
        funString = "fun(f) { f(1) + f(2) + f(3) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        splits = ForaNative.splitControlFlowGraph(cfg, "block_0Let")
        self.assertTrue(splits is not None)

    def test_cfgSplitting_7(self):
        funString = "fun(f) { f(1) + f(2) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        splits = ForaNative.splitControlFlowGraph(cfg, "block_0Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_8(self):
        funString = "fun(f) { (f(1), (f(1 + 3))) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_0Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_9(self):
        funString = "fun((f,g)) { 1 + (f() + g()) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_10(self):
        funString = "fun((f,g,h,k)) { (f(1) + g(2)) + (h(3) + k(4)) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_11(self):
        funString = "fun((f,g,h,k)) { f(1) + (g(2) + (h(3) + k(4))) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_12(self):
        funString = "fun((f,g,h)) { f(g(h(1),2),3) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is None)

    def test_cfgSplitting_13(self):
        funString = "fun((f,g,h,k)) { f(0) + f(g(1), h(2), k(3)) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is not None)

    def test_cfgSplitting_14(self):
        funString = "fun((f,g,h,k)) { k(f(1), g(2), h(3)) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        splits = ForaNative.splitControlFlowGraph(cfg, "block_7Let")

        self.assertTrue(splits is not None)

    def test_cannotSplitThingsWithMutables(self):
        text = """fun() {
            let s = fun(a,b,f) {
                if (b <= a)
                    return nothing
                if (b <= a + 1)
                    return f(a)

                let mid = Int64((a+b)/2)

                return s(a,mid,f) + s(mid,b,f)
                }
            let m = MutableVector.create(10,10);
            s(0,1000,fun(x){m[0] * x})
            }"""

        funImplval = FORA.extractImplValContainer(FORA.eval(text))

        i = 0
        while (i < 30000):
            i += 1000

            try:
                pausedComputation = callAndExtractPausedCompuationAfterSteps(funImplval, i)
            except NotInterruptedException as e:
                break


            allAreCST = True
            for val in pausedComputation.frames[0].values:
                if not val.isCST():
                    allAreCST = False
                    break

            if not allAreCST:
                splitComputation = ForaNative.splitPausedComputation(pausedComputation)

                self.assertTrue(not splitComputation, splitComputation)


    def test_splitComputation_1(self):
        text = """fun() {
            let s = fun(a,b,f) {
                if (b <= a)
                    return nothing
                if (b <= a + 1)
                    return f(a)

                let mid = Int64((a+b)/2)

                return s(a,mid,f) + s(mid,b,f)
                }
            let m = [0];
            s(0,1000,fun(x){m[0] * x})
            }"""

        funImplval = FORA.extractImplValContainer(FORA.eval(text))

        # minimum value to split seems to be 40
        pausedComputation = callAndExtractPausedCompuationAfterSteps(funImplval, 40)

        splitComputation = ForaNative.splitPausedComputation(pausedComputation)

        self.assertTrue(splitComputation is not None)


    def test_splitComputation_2(self):
        text = """fun() {
            let s = fun(a,b,f) {
                if (b <= a)
                    return nothing
                if (b <= a + 1)
                    return f(a)

                let mid = Int64((a+b)/2)

                return s(a,mid,f) + s(mid,b,f)
                }

            s(0,1000,fun(x){x})
            }"""

        funImplval = FORA.extractImplValContainer(FORA.eval(text))

        pausedComputation = callAndExtractPausedCompuationAfterSteps(funImplval, 35)

        splitComputation = ForaNative.splitPausedComputation(pausedComputation)
        self.assertIsNotNone(splitComputation)

        unsplitValue = finishPausedComputation(pausedComputation)

        applyComputationVal = finishPausedComputation(splitComputation.applyComputation)
        splitComputationVal = finishPausedComputation(splitComputation.splitComputation)

        resumedComputation = ForaNative.joinSplitPausedComputation(
                splitComputation,
                applyComputationVal,
                splitComputationVal
                )

        finalSplitVal = finishPausedComputation(resumedComputation)

        self.assertEqual(unsplitValue, finalSplitVal)

    def randomSplitComputationTest(self, text):
        if (isinstance(text, str)):
            funImplVal = FORA.extractImplValContainer(FORA.eval(text))
        else:
            funImplVal = text

        unsplitVal = callAndGetResult(funImplVal)

        splitAtLeastOne = False
        i = 0
        while (i < 3000):
            i += 1

            try:
                pausedComputation = callAndExtractPausedCompuationAfterSteps(funImplVal, i)
            except NotInterruptedException as e:
                break


            splitComputation = ForaNative.splitPausedComputation(pausedComputation)

            unsplitVal2 = finishPausedComputation(pausedComputation)
            self.assertEqual(unsplitVal, unsplitVal2)

            if (splitComputation):
                splitAtLeastOne = True

                applyComputationVal = finishPausedComputation(splitComputation.applyComputation)
                splitComputationVal = finishPausedComputation(splitComputation.splitComputation)

                resumedComputation = ForaNative.joinSplitPausedComputation(
                    splitComputation,
                    applyComputationVal,
                    splitComputationVal
                    )

                finalSplitVal = finishPausedComputation(resumedComputation)

                self.assertEqual(unsplitVal, finalSplitVal)

        if (not splitAtLeastOne):
            logging.warn("didn't split any versions of `%s`\nafter i = %s tries" % (text, i))

    def disabled_randomSplitting_1(self):
        funString = """
        fun() {
            let f = fun(x) { throw 0 };
            let g = fun(x) { while (true) { }; 1 };

            try { f(1) + g(2) }
            catch (e) { e == 0 };
            }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_2(self):
        funString = """
        fun() {
            let f = fun(x) { throw x };
            let g = fun(x) { throw x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_3(self):
        funString = """
        fun() {
            let f = fun(x) { throw x };
            let g = fun(x) { x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_4(self):
        funString = """
        fun() {
            let f = fun(x) { if (x) throw x; x };
            let g = fun(x) { x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_5(self):
        funString = """
        fun() {
            let f = fun(x) { x };
            let g = fun(x) { throw x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_6(self):
        funString = """
        fun() {
            let f = fun(x) { x };
            let g = fun(x) { x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_7(self):
        # doesn't ever split

        funString = """
        fun() {
            let f = fun(x) { if (x) throw 1; x; };
            let g = fun(x) { if (x) throw 2; x; };
            let h = fun(x) { if (x) throw 3; x; };

            try { f(try { g(4) } catch (e) { e }) + h(5) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_8(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { 2 };
            let h = fun(x) { 3 };

            try { f(g(4)) + h(5) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_9(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { throw 2 };
            let h = fun(x) { throw 3 };

            try { (f(4), g(5), h(6)) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

    def test_randomSplitting_10(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { throw 2 };
            let h = fun(x) { throw 3 };

            try { (f(4) + f(5)) + f(6) }
            catch (e) { e }
        }
        """

        self.randomSplitComputationTest(funString)

