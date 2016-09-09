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

import time
import unittest
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.Runtime as Runtime
import ufora.native.FORA as ForaNative
import ufora.FORA.TypedFora.TypedFora as TypedFora
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager
import ufora.native.CallbackScheduler as CallbackScheduler

PASS_COUNT = 100

aBigString = "a string that is big enough to cause refcounts"

class TestTypedForaLayouts(unittest.TestCase):
    def setUp(self):
        self.callbackScheduler = CallbackScheduler.singletonForTesting()

    def test_TypedFora_Layout_UsingCompiler(self):
        layoutStyles = [
            TypedFora.RefcountStyle.Pooled(),
            TypedFora.RefcountStyle.AsValueUnowned(),
            TypedFora.RefcountStyle.AsValueOwned()
            ]

        jovs = [
            ForaNative.parseStringToJOV("{String}"),
            #a small union
            ForaNative.parseStringToJOV("{Union([{String}, {Int64}])}"),
            #a much bigger union
            ForaNative.parseStringToJOV("{Union([{String}, {Int64}, {Float64}, nothing, ({Float64})])}"),

            ForaNative.parseStringToJOV("'%s'" % aBigString),
            ForaNative.parseStringToJOV("*")
            ]

        for ls1 in layoutStyles:
            for jov1 in jovs:
                for ls2  in layoutStyles:
                    for jov2 in jovs:
                        if not (ls1.isAsValueOwned() and ls2.isAsValueUnowned()):
                            t1 = TypedFora.Type(jov1, ls1)
                            t2 = TypedFora.Type(jov2, ls2)
                            self.runSimpleEvaluation(t1, t2)

    def runSimpleEvaluation(self, inputType, outputType):
        mainRuntime = Runtime.getMainRuntime()
        foraCompiler = mainRuntime.getTypedForaCompiler()

        while foraCompiler.anyCompilingOrPending():
            time.sleep(.01)

        aParticularStringValue = ForaNative.ImplValContainer(aBigString)

        callable = self.generateSimpleCallable(inputType, outputType)

        jumpTarget = foraCompiler.compile(callable)

        import gc
        gc.collect()

        for passIndex in range(PASS_COUNT):
            #type values are memoized, so we can't assume that the value has a refcount
            # of exactly one
            totalStringCount = ForaNative.totalStringCount()
            totalImplvalCount = ForaNative.totalImplvalCount()

            anExecutionContext = ExecutionContext.ExecutionContext(
                dataManager = VectorDataManager.constructVDM(self.callbackScheduler)
                )

            anExecutionContext.evaluateFunctionPointer(jumpTarget, aParticularStringValue)

            self.assertTrue(anExecutionContext.isFinished())

            res = anExecutionContext.getFinishedResult()

            self.assertTrue(not res.isException())
            self.assertEqual(res.asResult.result, aParticularStringValue)

            anExecutionContext.teardown()

            res = None

            #verify final refcounts
            self.assertEqual(
                aParticularStringValue.getStringObjectRefcount(),
                1,
                "refcounts weren't maintained in %s->%s. %s != 1" % (
                    inputType,
                    outputType,
                    aParticularStringValue.getStringObjectRefcount()
                    )
                )
            self.assertEqual(
                (totalStringCount, totalImplvalCount),
                (ForaNative.totalStringCount(), ForaNative.totalImplvalCount()),
                "refcounts weren't maintained in " + str(inputType) + "->" + str(outputType)
                )


    def generateSimpleCallable(self, inputType, outputType):
        var = TypedFora.Variable(0, inputType)

        expr = TypedFora.Expression.Var(var)

        if not outputType.jov.covers(inputType.jov):
            expr = TypedFora.Expression.CastWithoutCheck(
                expr,
                outputType
                )

        return TypedFora.Callable.SingleExpression(
            TypedFora.VariableList([var]),
            expr,
            outputType,
            False,
            False
            )

