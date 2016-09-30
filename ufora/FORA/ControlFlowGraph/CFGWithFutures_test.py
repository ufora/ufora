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
import numpy
import random

import ufora.FORA.python.ForaValue as ForaValue
import ufora.native.FORA as ForaNative
import ufora.FORA.python.FORA as FORA

emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])

def normalComputationResult(result):
    return ForaNative.ComputationResult.Result(
            result,
            ForaNative.ImplValContainer()
            )

def exceptionComputationResult(result):
    return ForaNative.ComputationResult.Exception(
            result,
            ForaNative.ImplValContainer()
            )

def evalSubmittableArgs(submittableArgs):
    def evalApplyTuple(applyTuple, signature = None):
        varNames = map(lambda ix: "x_%s" % ix, range(len(applyTuple)))
        if signature is None:
            evalStringTerms = varNames
        else:
            evalStringTerms = []
            for ix in range(len(signature.terms)):
                term = signature.terms[ix]
                if term.isNormal():
                    name = term.asNormal.name
                    if name is not None:
                        evalStringTerms.append("%s: x_%s" % (name, ix))
                    else:
                        evalStringTerms.append("x_%s" % ix)
                elif term.isTupleCall():
                    evalStringTerms.append("*x_%s" % ix)

        evalString = evalStringTerms[0] + "`(" + ",".join(evalStringTerms[1:]) + ")"

        try:
            return normalComputationResult(
                FORA.extractImplValContainer(
                    FORA.eval(
                        evalString,
                        locals = { name: val
                                   for (name, val) in
                                   zip(varNames, applyTuple) },
                        keepAsForaValue = True
                    )
                )
            )
        except ForaValue.FORAException as e:
            return exceptionComputationResult(
                FORA.extractImplValContainer(e.foraVal)
            )

    if submittableArgs.isApply():
        return evalApplyTuple(
            submittableArgs.args.values,
            submittableArgs.args.signature
        )
    else: # submittableArgs.isCached()
        tr = ()

        # this corresponds to the logic for Cached nodes in
        # CFGWithFutures::asSubmittable
        assert len(submittableArgs.args.values) == 1

        for cachedPair in submittableArgs.args.values[0]:
            applyArgs = [cachedPair[0], ForaNative.makeSymbol("Call")]
            applyArgs.extend(cachedPair[1])

            res = evalApplyTuple(applyArgs)

            if res.isException():
                return res

            tr = tr + (res.asResult.result,)

        return normalComputationResult(ForaNative.ImplValContainer(tr))

def serialSimulation(cfg, nodeValues, entryPoint=None):
    cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
        cfg, entryPoint, nodeValues)

    return simulateWithFuturesSerially(cfgWithFutures)

def simulateWithFuturesSerially(cfgWithFutures):
    currentLabel = None

    shouldContinue = True
    while shouldContinue or not cfgWithFutures.hasResolvedToSimpleState():
        print cfgWithFutures

        body = cfgWithFutures.currentNode().body
        currentLabel = cfgWithFutures.currentLabel()
        if body.isApply() or body.isCached():
            body = cfgWithFutures.currentNode().body
            submittableFutures = cfgWithFutures.indicesOfSubmittableFutures()
            futureIx = submittableFutures[0]
            submittableArgs = cfgWithFutures.submittableArgs(futureIx)

            cfgWithFutures.slotCompleted(
                futureIx, evalSubmittableArgs(submittableArgs)
            )
            shouldContinue = cfgWithFutures.continueSimulation()
        else:
            shouldContinue = cfgWithFutures.continueSimulation()

    return cfgWithFutures

def randomOrderSimulation(cfg, nodeValues, entryPoint=None):
    cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
        cfg, entryPoint, nodeValues)

    return simulateWithFuturesInRandomOrder(cfgWithFutures)

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
        madeProgress = False
        for ix in range(1 + numpy.random.randint(5)):
            madeProgress |= cfgWithFutures.continueSimulation()

        return madeProgress

    def evaluateAFuture():
        slotIx = random.choice(list(futuresToEvaluate))
        applyTuple = cfgWithFutures.submittableArgs(slotIx)
        result = evalSubmittableArgs(applyTuple)
        futuresToEvaluate.remove(slotIx)

        return slotIx, result

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

class CFGWithFuturesTest(unittest.TestCase):
    def parseStringToFunction(self, expr):
        expression = ForaNative.parseStringToExpression(
            expr, emptyCodeDefinitionPoint, "")

        return expression.extractRootLevelCreateFunctionPredicate()

    # note for the reader: in order for these test_futures_XXX tests to
    # make sense, one might want to look at a string representation of the
    # relevant CFG

    def test_futures_1(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)

        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        self.assertEqual(cfgWithFutures.currentLabel(), "block_0Let")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        asSubmittable = cfgWithFutures.submittableArgs(0)

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.currentLabel(), "block_1Let")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        self.assertIsNotNone(cfgWithFutures.submittableArgs(1))

        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])
        self.assertIsNone(cfgWithFutures.submittableArgs(2))
        self.assertIsNone(cfgWithFutures.submittableArgs(3))

    def test_futures_2(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.submittableArgs(0)
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])

        cfgWithFutures.submittableArgs(1)
        cfgWithFutures.slotCompleted(
            1, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [2])

        cfgWithFutures.submittableArgs(2)
        cfgWithFutures.slotCompleted(
            2, normalComputationResult(ForaNative.ImplValContainer(5))
            )

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(5)
            )

    def test_futures_3(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.submittableArgs(1)
        cfgWithFutures.slotCompleted(
            1, normalComputationResult(ForaNative.ImplValContainer(3))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.submittableArgs(0)
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [2])

        cfgWithFutures.submittableArgs(2)
        cfgWithFutures.slotCompleted(
            2, normalComputationResult(ForaNative.ImplValContainer(5))
            )

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(5)
            )

    def test_futures_4(self):
        funString = "fun(f) { f(0) + (f(1) * f(2)) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)
        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        for ix in range(3):
            cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1, 2])

        for ix in range(3):
            cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1, 2])

        cfgWithFutures.submittableArgs(2)
        cfgWithFutures.slotCompleted(
            2, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.submittableArgs(1)
        cfgWithFutures.slotCompleted(
            1, normalComputationResult(ForaNative.ImplValContainer(1))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 3])

        cfgWithFutures.submittableArgs(3)
        cfgWithFutures.slotCompleted(
            3, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.submittableArgs(0)
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(0))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [4])

        cfgWithFutures.submittableArgs(4)
        cfgWithFutures.slotCompleted(
            4, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])

        self.assertEqual(cfgWithFutures.currentLabel(), "block_2Try")

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(2)
            )

    def test_futures_5(self):
        funString = "fun(f) { f(0) + f(1) + f(2) }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        for ix in range(3):
            cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1, 3])

        cfgWithFutures.submittableArgs(3)
        cfgWithFutures.slotCompleted(
            3, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.submittableArgs(1)
        cfgWithFutures.slotCompleted(
            1, normalComputationResult(ForaNative.ImplValContainer(1))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.submittableArgs(0)
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(0))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [2])

        cfgWithFutures.submittableArgs(2)
        cfgWithFutures.slotCompleted(
            2, normalComputationResult(ForaNative.ImplValContainer(2))
            )
        cfgWithFutures.continueSimulation()

        cfgWithFutures.submittableArgs(4)
        cfgWithFutures.slotCompleted(
            4, normalComputationResult(ForaNative.ImplValContainer(4))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])

        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(4)
            )

    def test_futures_6(self):
        funString = "fun(f, x) { let res = f(*x); res }"
        cfg = self.parseStringToFunction(funString).toCFG(2)

        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { size(x) }"))
        xImplVal = ForaNative.ImplValContainer((1,2,3));

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (fImplval, xImplVal))

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])
        cfgWithFutures.submittableArgs(0)

    def test_futures_7(self):
        funString = "fun(f, x) { let res = f(x, *x); res + 1 }"
        cfg = self.parseStringToFunction(funString).toCFG(2)

        fImplval = FORA.extractImplValContainer(FORA.eval("fun(*x) { size(x) }"))
        xImplVal = ForaNative.ImplValContainer((1,2,3));

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (fImplval, xImplVal))

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])
        cfgWithFutures.submittableArgs(0)

        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(4))
            )
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])

        cfgWithFutures.slotCompleted(
            1, normalComputationResult(ForaNative.ImplValContainer(5))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())
        cfgWithFutures.continueSimulation()
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(5)
            )

    def assertComponentwiseEqual(self, x, y):
        self.assertEqual(len(x), len(y))

        for ix in range(len(x)):
            self.assertEqual(x[ix], y[ix])

    def test_futures_tupleCallInContinuation_1(self):
        text = "fun(x) { x = x + x; size((x, *x)) }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        tup = (1,2,3)
        xImplVal = ForaNative.ImplValContainer(tup)
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_1Let", (xImplVal,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        tup = tup + tup
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(
                ForaNative.ImplValContainer(tup)
                )
            )

        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])
        self.assertComponentwiseEqual(
            cfgWithFutures.submittableArgs(1).args.values,
            [ForaNative.makeSymbol("size"), ForaNative.makeSymbol("Call"),
             ForaNative.ImplValContainer((tup,1,2,3,1,2,3))]
            )

    def test_futures_tupleCallInContinuation_2(self):
        text = "fun(x) { x = x + x; size((x, *x)) }"

        cfg = self.parseStringToFunction(text).toCFG(1)

        x = 1
        xImplVal = ForaNative.ImplValContainer(x)
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_1Let", (xImplVal,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        x = x + x
        cfgWithFutures.slotCompleted(
            0, normalComputationResult(
                ForaNative.ImplValContainer(x)
                )
            )

        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])
        self.assertComponentwiseEqual(
            cfgWithFutures.submittableArgs(1).args.values,
            [ForaNative.makeSymbol("size"), ForaNative.makeSymbol("Call"),
             ForaNative.ImplValContainer((x, x))]
            )

    def test_futures_with_exceptions_1(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        funImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { throw 42; }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.slotCompleted(
            0, exceptionComputationResult(ForaNative.ImplValContainer(42))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())
        self.assertTrue(cfgWithFutures.mustBailEarly())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertTrue(finalResult.asPaused.frame.label, "block_0Let")

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, finalResult.asPaused.frame.label,
            finalResult.asPaused.frame.values
            )

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, exceptionComputationResult(ForaNative.ImplValContainer(1337))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asException.exception,
            ForaNative.ImplValContainer(1337)
            )

    def test_futures_with_exceptions_2(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        funImplval = FORA.extractImplValContainer(
            FORA.eval("fun(x) { throw 42; }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.slotCompleted(
            1, exceptionComputationResult(ForaNative.ImplValContainer(42))
            )
        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())
        self.assertTrue(cfgWithFutures.mustBailEarly())

        cfgWithFutures.slotCompleted(
            0, normalComputationResult(ForaNative.ImplValContainer(420))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(finalResult.asPaused.frame.label, "block_4Throw")

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, finalResult.asPaused.frame.label, finalResult.asPaused.frame.values
            )

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, exceptionComputationResult(ForaNative.ImplValContainer(1337))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asException.exception,
            ForaNative.ImplValContainer(1337)
        )

    def test_futures_with_exceptions_3(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        funImplval = FORA.extractImplValContainer(
            FORA.eval("fun(x) { throw 42; }"))
        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, "block_0Let", (funImplval,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.slotCompleted(
            1, exceptionComputationResult(ForaNative.ImplValContainer(42))
            )
        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())
        self.assertTrue(cfgWithFutures.mustBailEarly())

        cfgWithFutures.slotCompleted(
            0, exceptionComputationResult(ForaNative.ImplValContainer(420))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(finalResult.asPaused.frame.label, "block_5Throw")

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, finalResult.asPaused.frame.label,
            finalResult.asPaused.frame.values
            )

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, exceptionComputationResult(ForaNative.ImplValContainer(1337))
            )
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asException.exception,
            ForaNative.ImplValContainer(1337)
            )

    def test_futures_with_branching_1(self):
        cfg = self.parseStringToFunction(
            "fun(x, f, g) { if (x) return f(x) else g(x) }").toCFG(3)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        gImplVal = FORA.extractImplValContainer(FORA.eval("fun(x) { throw x }"))
        xImplVal = ForaNative.ImplValContainer(1)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal, fImplval, gImplVal))

        self.assertEqual(cfgWithFutures.currentLabel(), "block_0Branch")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.currentLabel(), "block_1Return")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(2)
            )

    def test_futures_with_branching_2(self):
        text = "fun(x, f) { let res = f(x); if (res) 0 else 1 }"
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        xImplVal = ForaNative.ImplValContainer(1)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal, fImplval))

        self.assertEqual(cfgWithFutures.currentLabel(), "block_0Let")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.currentLabel(), "block_1Branch")

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        cfgWithFutures.continueSimulation()

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()
        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(0)
            )

    def test_loop_unrolling(self):
        text = """fun(f) {
                      let res = 0;
                      let ix = 0;
                      while (true)
                          {
                          f(ix);
                          ix = ix + 1
                          }
                      res
                      }"""
        cfg = self.parseStringToFunction(text).toCFG(1)
        fImplVal = FORA.extractImplValContainer(FORA.eval("fun(x) { x ** 2 }"))

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (fImplVal,)
            )

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(len(cfgWithFutures.indicesOfSubmittableFutures()), 2)

        cfgWithFutures.slotCompleted(
            1, evalSubmittableArgs(cfgWithFutures.submittableArgs(1))
            )

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(len(cfgWithFutures.indicesOfSubmittableFutures()), 3)

        cfgWithFutures.slotCompleted(
            3, evalSubmittableArgs(cfgWithFutures.submittableArgs(3))
            )

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(len(cfgWithFutures.indicesOfSubmittableFutures()), 4)

    def test_switch_nodes_1(self):
        text = "fun(x, f, g) { match (x) with (1) { f(x) } (2) { g(x) } }"
        cfg = self.parseStringToFunction(text).toCFG(3)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        gImplVal = FORA.extractImplValContainer(FORA.eval("fun(x) { throw x }"))
        xImplVal = ForaNative.ImplValContainer(1)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal, fImplval, gImplVal))

        self.assertEqual(cfgWithFutures.currentLabel(), "block_0Try")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [])

        cfgWithFutures.continueSimulation()

        self.assertEqual(cfgWithFutures.currentLabel(), "block_6Try")

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        finalResult = cfgWithFutures.getFinalResult()
        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(2)
            )

    def test_switch_nodes_2(self):
        text = """fun(x, f) {
                      let res = f(x);
                      match (res) with
                            (1) { -1 }
                            (2) { -2 }
                      }"""
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
        xImplVal = ForaNative.ImplValContainer(1)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal, fImplval))

        self.assertEqual(cfgWithFutures.currentLabel(), "block_0Let")
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_1Try")

        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_5Try")

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [1])

        cfgWithFutures.slotCompleted(
            1, evalSubmittableArgs(cfgWithFutures.submittableArgs(1))
            )

        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.currentLabel(), "block_5Try")

        finalResult = cfgWithFutures.getFinalResult()
        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(-2)
            )

    def test_tupleExpand_nodes_1(self):
        text = "fun(h) { let (f, g) = h(); (f(), g()) }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        hImplVal = FORA.extractImplValContainer(
            FORA.eval(
                "fun() { let f = fun() { 1 }; let g = fun() { 2 }; (f, g) }"
                )
            )

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (hImplVal,))

        res = evalSubmittableArgs(cfgWithFutures.submittableArgs(0))

        cfgWithFutures.slotCompleted(
            0, res
            )

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        submittableArgs = cfgWithFutures.submittableArgs(1)

        cfgWithFutures.slotCompleted(
            1, evalSubmittableArgs(submittableArgs)
            )
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [2])

        # this verifies that parallelism is possible for `text`
        cfgWithFutures.continueSimulation()
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [2, 3])

        """
        # the following result in fora exceptions, due to python interop problems.
        # (specifically they are illegal python applies)
        cfgWithFutures.slotCompleted(
            2, evalSubmittableArgs(cfgWithFutures.submittableArgs(2))
            )
        cfgWithFutures.slotCompleted(
            3, evalSubmittableArgs(cfgWithFutures.submittableArgs(3))
            )
        """

    def test_tupleExpand_with_star_args(self):
        text = "fun(x) { let (y, z, *args) = x; args; }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        xImplVal = ForaNative.ImplValContainer((1,2,3,4))

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal,))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        cfgWithFutures.continueSimulation()

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer((3,4))
            )

    def test_cached_nodes_1(self):
        text = "fun(f, g) { cached(f(), g()); }"
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun() { 1 }"))
        gImplVal = FORA.extractImplValContainer(FORA.eval("fun() { 2 }"))

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (fImplval, gImplVal))

        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0])

        res = evalSubmittableArgs(cfgWithFutures.submittableArgs(0))

        expectedResult = ForaNative.ImplValContainer((1, 2))

        self.assertEqual(res.asResult.result, expectedResult)

        cfgWithFutures.slotCompleted(0, res)

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            expectedResult
            )

    def test_cached_nodes_2(self):
        text = """fun() {
                      let f = fun() { throw 0 };
                      let g = fun() { 1 };
                      cached(f(), g())
                      }"""
        cfg = self.parseStringToFunction(text).toCFG(0)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, ())

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        self.assertEqual(
            cfgWithFutures.getFinalResult().asResult.result.asException.exception,
            ForaNative.ImplValContainer(0)
            )

    def test_cached_nodes_3(self):
        text = """fun() {
                      let f = fun() { 0 };
                      let g = fun() { throw 1 };
                      cached(f(), g())
                      }"""
        cfg = self.parseStringToFunction(text).toCFG(0)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, ())

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        self.assertEqual(
            cfgWithFutures.getFinalResult().asResult.result.asException.exception,
            ForaNative.ImplValContainer(1)
            )

    def test_cfg_with_no_applies(self):
        text = "fun() { if (1) true else false }"
        cfg = self.parseStringToFunction(text).toCFG(0)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, ())

        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        self.assertEqual(
            cfgWithFutures.getFinalResult().asResult.result.asResult.result,
            ForaNative.ImplValContainer(True)
            )

    def test_return_MakeTuple(self):
        text = "fun() { let res = 1 + 1; (res, 1,2,3) }"
        cfg = self.parseStringToFunction(text).toCFG(0)

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, ())

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        cfgWithFutures.continueSimulation()

        self.assertEqual(
            cfgWithFutures.getFinalResult().asResult.result.asResult.result,
            ForaNative.ImplValContainer((2,1,2,3))
            )

    def test_tuple_args_1(self):
        text = "fun(f, x) { f(*x) }"
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(
            FORA.eval("let f = fun(x, y, z) { x + y + z }; f")
            )
        xImplVal = ForaNative.ImplValContainer((1,2,3));

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (fImplval, xImplVal))

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        self.assertEqual(
            cfgWithFutures.getFinalResult().asResult.result.asResult.result,
            ForaNative.ImplValContainer(6)
            )

    def test_cant_simulate_with_mutable_args(self):
        text = "fun(x) { }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        xImplVal = FORA.extractImplValContainer(
            FORA.eval("MutableVector(Int64).create(10, 0)")
            )

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (xImplVal,))

        print cfgWithFutures

        self.assertIsNone(cfgWithFutures)

    def test_mutable_values_1(self):
        text = "fun(f, g) { let x = f(); let y = g(); 1 }"
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(
            FORA.eval("let f = fun() { MutableVector(Int64).create(5, 0) }; f")
            )
        gImplval = FORA.extractImplValContainer(
            FORA.eval("let g = fun() { MutableVector(Float64).create(10, 0.0) }; g")
            )

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (fImplval, gImplval))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.slotCompleted(
            1, evalSubmittableArgs(cfgWithFutures.submittableArgs(1))
            )

        self.assertTrue(cfgWithFutures.mustBailEarly())
        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        self.assertTrue(cfgWithFutures.mustBailEarly())
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()
        pausedFrame = finalResult.asPaused.frame

        self.assertEqual(pausedFrame.label, "block_1Let")
        self.assertEqual(len(pausedFrame.values), 1)
        self.assertEqual(pausedFrame.values[0], gImplval)

    def test_mutable_values_2(self):
        text = "fun(f, g) { let x = f(); let y = g(); 1 }"
        cfg = self.parseStringToFunction(text).toCFG(2)
        fImplval = FORA.extractImplValContainer(
            FORA.eval("let f = fun() { Vector.range(10) }; f")
            )
        gImplval = FORA.extractImplValContainer(
            FORA.eval("let g = fun() { MutableVector(Float64).create(10, 0.0) }; g")
            )

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(
            cfg, None, (fImplval, gImplval))

        cfgWithFutures.continueSimulation()
        cfgWithFutures.continueSimulation()

        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())
        self.assertEqual(cfgWithFutures.indicesOfSubmittableFutures(), [0, 1])

        cfgWithFutures.slotCompleted(
            1, evalSubmittableArgs(cfgWithFutures.submittableArgs(1))
            )

        self.assertTrue(cfgWithFutures.mustBailEarly())
        self.assertFalse(cfgWithFutures.hasResolvedToSimpleState())

        cfgWithFutures.slotCompleted(
            0, evalSubmittableArgs(cfgWithFutures.submittableArgs(0))
            )

        self.assertTrue(cfgWithFutures.mustBailEarly())
        self.assertTrue(cfgWithFutures.hasResolvedToSimpleState())

        finalResult = cfgWithFutures.getFinalResult()

        self.assertEqual(
            finalResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(1)
            )

    def serialResult(self, cfg, nodeValues, entryPoint=None):
        serial = serialSimulation(cfg, nodeValues, entryPoint)
        return serial.getFinalResult()

    def seed(self, seed):
        numpy.random.seed(seed)
        random.seed(seed)

    def fuzz(self, cfg, nodeValues, seed, entryPoint=None):
        serialResult = self.serialResult(cfg, nodeValues, entryPoint)

        self.seed(seed)

        for ix in range(10):
            randomOrderResult = randomOrderSimulation(
                cfg, nodeValues, entryPoint).getFinalResult()
            self.assertEqual(
                randomOrderResult,
                serialResult,
                "at ix = %s, unexpectedly got diFferent results \n%s\nvs\n%s"
                "\nisResult? %s vs %s"
                % (ix, repr(randomOrderResult), repr(serialResult),
                   randomOrderResult.isResult(), serialResult.isResult())
            )

    def test_future_fuzz_1(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun(x) { x + 1 }")),)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_2(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) + f(3) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun(x) { x + 1 }")),)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_3(self):
        cfg = self.parseStringToFunction(
            "fun(f) { f(1) + f(2) + f(3) + f(4) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun(x) { x + 1 }")),)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_4(self):
        cfg = self.parseStringToFunction(
            "fun(f) { f(1) + f(2) + f(3) + f(4) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun(x) { if (x == 3) throw x else x + 1 }")),)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_5(self):
        cfg = self.parseStringToFunction(
            "fun(f) { f(1) + f(2) + f(3) + f(4) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun(x) { if (x <= 2) throw x else x + 1 }")),)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_6(self):
        funString = "fun(f, x) { let res = f(x, *x); res + 1 }"
        cfg = self.parseStringToFunction(funString).toCFG(2)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(*x) { size(x) }"))
        xImplVal = ForaNative.ImplValContainer((1,2,3));
        nodeValues = (fImplval, xImplVal)

        self.fuzz(cfg, nodeValues, 10)

    def test_future_fuzz_7(self):
        text = "fun(x) { x = x + x; size((x, *x)) }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        xImplVal = ForaNative.ImplValContainer((1,2,3))
        nodeValues = (xImplVal,)

        self.fuzz(cfg, nodeValues, 10)

    def test_serialResults_1(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }")),)

        serialResult = self.serialResult(cfg, nodeValues)

        self.assertEqual(
            serialResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(5)
            )

        serialResult2 = self.serialResult(cfg, nodeValues)

        self.assertEqual(serialResult, serialResult2)

    def test_serialResults_2(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) + f(3) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(FORA.eval("fun(x) { x }")),)

        serialResult = self.serialResult(cfg, nodeValues)

        self.assertEqual(
            serialResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(6)
            )

    def test_serialResults_3(self):
        funString = "fun(f, x) { let res = f((x, *x)); res + 1 }"
        cfg = self.parseStringToFunction(funString).toCFG(2)
        fImplval = FORA.extractImplValContainer(FORA.eval("fun(x) { size(x) }"))
        xImplVal = ForaNative.ImplValContainer((1,2,3))
        nodeValues = (fImplval, xImplVal)

        serialResult = self.serialResult(cfg, nodeValues, "block_5Let")

        self.assertEqual(
            serialResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(5)
            )

    def test_serialResults_4(self):
        text = "fun(x) { x = x + x; size((x, *x)) }"
        cfg = self.parseStringToFunction(text).toCFG(1)

        tup = (1,2,3)
        xImplVal = ForaNative.ImplValContainer(tup)
        serialResult = self.serialResult(cfg, (xImplVal,), "block_1Let")

        self.assertEqual(
            serialResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(7)
            )

    def test_serialResults_5(self):
        text = "fun(x) { x = x + x; size((x, *x)) }"
        cfg = self.parseStringToFunction(text).toCFG(1)

        xImplVal = ForaNative.ImplValContainer(1)
        serialResult = self.serialResult(cfg, (xImplVal,), "block_1Let")

        self.assertEqual(
            serialResult.asResult.result.asResult.result,
            ForaNative.ImplValContainer(2)
            )

    def test_matching(self):
        funString = "fun(p) { match(p) with (#P()) { 1 } (...) { 0 } }"
        cfg = self.parseStringToFunction(funString).toCFG(1)

        p = FORA.extractImplValContainer(FORA.eval("#P()"))

        cfgWithFutures = ForaNative.CFGWithFutures.createCfgWithFutures(cfg, "block_0Try", (p,))

        simulateWithFuturesSerially(cfgWithFutures)

        final = cfgWithFutures.getFinalResult()

        self.assertTrue(final.isResult())
        self.assertTrue(final.asResult.result.isResult())
        self.assertEqual(final.asResult.result.asResult.result.pyval, 1)

    # this test was disabled due to a refcounting bug in ControlFlowGraph/SimulationState:
    # the example is something like: bla = f(args) where bla is not consumed anywhere else
    # and args is not yet current, and there are some subsequent calculations
    # eventually bla leaves the current set of slot args, and then gets decrefed and we are dead
    def disabled_garbage_collection_with_serial_applies(self):
        cfg = self.parseStringToFunction("fun(f) { f(1) + f(2) + f(3) }").toCFG(1)
        nodeValues = (FORA.extractImplValContainer(FORA.eval("fun(x) { x }")),)

        serial = serialSimulation(cfg, nodeValues)

        self.assertTrue(serial.getSlots()[0].isGarbageCollected())
        self.assertTrue(serial.getSlots()[1].isGarbageCollected())
        self.assertFalse(serial.getSlots()[2].isGarbageCollected())

        self.seed(10)

        for ix in range(10):
            randomOrder = randomOrderSimulation(cfg, nodeValues)
            self.assertTrue(randomOrder.getSlots()[0].isGarbageCollected())
            self.assertTrue(randomOrder.getSlots()[1].isGarbageCollected())
            self.assertFalse(randomOrder.getSlots()[2].isGarbageCollected())

    def disabled_garbage_collection_with_branch(self):
        cfg = self.parseStringToFunction(
            "fun(f) { let res = f(1); if (res) 1 + 1 else res 1 - 1 }").toCFG(1)

        nodeValues = (FORA.extractImplValContainer(FORA.eval("fun(x) { x }")),)

        serial = serialSimulation(cfg, nodeValues)

        self.assertTrue(serial.getSlots()[0].isGarbageCollected())

        self.seed(10)

        for ix in range(10):
            randomOrder = randomOrderSimulation(cfg, nodeValues)
            self.assertTrue(randomOrder.getSlots()[0].isGarbageCollected())

    def disabled_garbage_collection_with_switch(self):
        cfg = self.parseStringToFunction(
            "fun(x, f, g) { match (f(x)) with (1) { g(1) } (2) { g(2) } }"
            ).toCFG(3)

        nodeValues = (ForaNative.ImplValContainer(1),
                      FORA.extractImplValContainer(FORA.eval("fun(x) { x }")),
                      FORA.extractImplValContainer(FORA.eval("fun(x) { x + 1 }"))
                      )

        serial = serialSimulation(cfg, nodeValues)

        self.assertTrue(serial.getSlots()[0].isGarbageCollected())

        self.seed(10)

        for ix in range(10):
            randomOrder = randomOrderSimulation(cfg, nodeValues)
            self.assertTrue(randomOrder.getSlots()[0].isGarbageCollected())

    def disabled_garbage_collection_with_tupleExpand(self):
        text = "fun(h) { let (f, g) = h(); (f(), g()) }"
        cfg = self.parseStringToFunction(text).toCFG(1)
        nodeValues = (FORA.extractImplValContainer(
            FORA.eval("fun() { let f = fun() { 1 }; let g = fun() { 2 }; (f, g) }")
            ),)

        serial = serialSimulation(cfg, nodeValues)

        self.assertTrue(serial.getSlots()[0].isGarbageCollected())

        self.seed(10)

        for ix in range(10):
            randomOrder = randomOrderSimulation(cfg, nodeValues)
            self.assertTrue(randomOrder.getSlots()[0].isGarbageCollected())

