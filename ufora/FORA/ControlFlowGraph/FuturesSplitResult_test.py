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
import numpy
import random

import ufora.native.FORA as ForaNative
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.FORA as FORA
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

from ufora.FORA.ControlFlowGraph.ControlFlowGraphSplitter_test import \
    NotInterruptedException, callAndExtractPausedCompuationAfterSteps

from ufora.FORA.ControlFlowGraph.CFGWithFutures_test import \
    normalComputationResult, exceptionComputationResult, evalSubmittableArgs

def callAndGetResult(funImplVal):
    vdm = ForaNative.VectorDataManager(callbackScheduler, 50 * 1024 * 1024)
    
    context = ExecutionContext.ExecutionContext(
        dataManager = vdm,
        allowInterpreterTracing = False
        )
        
    context.evaluate(funImplVal, ForaNative.symbol_Call)

    finishedResult = context.getFinishedResult()

    return finishedResult

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

    return finishedResult

def getFinalResultSerially(futuresSplitResult):
    return getFinalResult_(futuresSplitResult, False)

def getFinalResultInRandomOrder(futuresSplitResult):
    return getFinalResult_(futuresSplitResult, True)
def simulateWithFuturesSerially(cfgWithFutures):
    shouldContinue = True
    while shouldContinue or not cfgWithFutures.hasResolvedToSimpleState():
        body = cfgWithFutures.currentNode().body
        if body.isApply() or body.isCached():
            body = cfgWithFutures.currentNode().body
            submittableFutures = cfgWithFutures.indicesOfSubmittableFutures()
            futureIx = submittableFutures[0]
            submittableArgs = cfgWithFutures.submittableArgs(futureIx)

            computationResult = finishPausedComputation(
                submittableArgs.toPausedComputation())

            cfgWithFutures.slotCompleted(
                futureIx, computationResult
            )
            shouldContinue = cfgWithFutures.continueSimulation()
        else:
            shouldContinue = cfgWithFutures.continueSimulation()

    return cfgWithFutures

def simulateWithFuturesInRandomOrder(cfgWithFutures):
    futuresToEvaluate = set()

    def grabSomeSubmittableFutures():
        submittableFutures = cfgWithFutures.indicesOfSubmittableFutures()

        if len(submittableFutures) == 0:
            return

        for ix in range(numpy.random.randint(3)):
            futuresToEvaluate.add(random.choice(submittableFutures))
                
    def shouldEvaluateAFuture():
        if len(futuresToEvaluate) == 0:
            return False
                
        return numpy.random.random_sample() < 0.5

    def continueSimulating():
        for ix in range(1 + numpy.random.randint(5)):
            cfgWithFutures.continueSimulation()

    def evaluateAFuture():
        slotIx = random.choice(list(futuresToEvaluate))
        applyTuple = cfgWithFutures.submittableArgs(slotIx)
        
        computationResult = finishPausedComputation(applyTuple.toPausedComputation())

        futuresToEvaluate.remove(slotIx)
            
        return slotIx, computationResult

    shouldContinue = True
    while shouldContinue or not cfgWithFutures.hasResolvedToSimpleState():
        grabSomeSubmittableFutures()
        if shouldEvaluateAFuture():
            slotIx, result = evaluateAFuture()
            cfgWithFutures.slotCompleted(
                slotIx, result
            )
        shouldContinue = continueSimulating()

    return cfgWithFutures

def getFinalResult_(futuresSplitResult, randomOrder):
    slotZeroComputation = futuresSplitResult.pausedComputationForSlot(0)

    slotZeroComputationResult = finishPausedComputation(slotZeroComputation)

    if slotZeroComputationResult.isResult():
        futuresSplitResult.slotCompleted(
            0, normalComputationResult(
                slotZeroComputationResult.asResult.result
                )
        )
    else:
        futuresSplitResult.slotCompleted(
            0, exceptionComputationResult(
                slotZeroComputationResult.asException.exception
                )
        )

    futuresSplitResult.continueSimulation()

    if randomOrder:
        simulateWithFuturesInRandomOrder(futuresSplitResult)
    else:
        simulateWithFuturesSerially(futuresSplitResult)

    return futuresSplitResult.getFinalResult()

class FuturesSplitResultTest(unittest.TestCase):
    def seed(self, seed):
        numpy.random.seed(seed)
        random.seed(seed)

    def setUp(self):
        self.seed(42)

    def randomSplitWithFuturesTest(self, text, low = 0, high = 3000, stride=10):
        if (isinstance(text, str)):
            funImplVal = FORA.extractImplValContainer(FORA.eval(text))
        else:
            funImplVal = text

        unsplitVal = callAndGetResult(funImplVal)

        splitAtLeastOne = False
        ix = low
        while (ix < high):
            ix += stride
            
            try:
                pausedComputation = callAndExtractPausedCompuationAfterSteps(
                    funImplVal, ix)
            except NotInterruptedException as e:
                break

            splitWithFutures = ForaNative.FuturesSplitResult\
                                         .splitPausedComputation(pausedComputation)
                
            unsplitVal2 = finishPausedComputation(pausedComputation)
            self.assertEqual(unsplitVal, unsplitVal2)

            if splitWithFutures:
                splitAtLeastOne = True

                # random order simulation
                nextPausedComputation = getFinalResultInRandomOrder(splitWithFutures)
                finalResult = finishPausedComputation(nextPausedComputation)

                self.assertEqual(unsplitVal, finalResult)

                # serial simulation
                splitWithFutures = ForaNative.FuturesSplitResult\
                                   .splitPausedComputation(pausedComputation)

                nextPausedComputation = getFinalResultSerially(splitWithFutures)

                finalResult = finishPausedComputation(nextPausedComputation)
                self.assertEqual(unsplitVal, finalResult)

        self.assertTrue(splitAtLeastOne)

    def test_randomSplittingWithFutures_1(self):
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

        self.randomSplitWithFuturesTest(text, low=0, high=1000)

    def test_randomSplittingWithFutures_2(self):
        funString = """
        fun() {
            let f = fun(x) { throw x };
            let g = fun(x) { throw x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_3(self):
        funString = """
        fun() {
            let f = fun(x) { throw x };
            let g = fun(x) { x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_4(self):
        funString = """
        fun() {
            let f = fun(x) { if (x) throw x; x };
            let g = fun(x) { x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_5(self):
        funString = """
        fun() {
            let f = fun(x) { math.sin(x) };
            let g = fun(x) { math.cos(x) };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplitting_6(self):
        funString = """
        fun() {
            let f = fun(x) { x };
            let g = fun(x) { throw x };

            try { f(1) + g(2) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_7(self):
        funString = """
        fun() {
            let f = fun(x) { if (x) throw 1; x; };
            let g = fun(x) { if (x) throw 2; x; };
            let h = fun(x) { if (x) throw 3; x; };

            try { f(try { g(4) } catch (e) { e }) + h(5) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_8(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { 2 };
            let h = fun(x) { 3 };

            try { f(g(4)) + h(5) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_9(self):
        funString = """
        fun() {
            let f = fun(x) { 1 };
            let g = fun(x) { throw 2 };
            let h = fun(x) { throw 3 };

            try { f(g(4)) + h(5) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_10(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { throw 2 };
            let h = fun(x) { throw 3 };

            try { (f(4), g(5), h(6)) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

    def test_randomSplittingWithFutures_11(self):
        funString = """
        fun() {
            let f = fun(x) { throw 1 };
            let g = fun(x) { throw 2 };
            let h = fun(x) { throw 3 };

            try { f(4) + f(5) + f(6) }
            catch (e) { e }
        }
        """

        self.randomSplitWithFuturesTest(funString, low=0, high=10, stride=1)

