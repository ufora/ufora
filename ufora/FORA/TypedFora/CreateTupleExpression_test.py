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
import ufora.FORA.python.ExecutionContext as ExecutionContext
import ufora.FORA.python.Runtime as Runtime
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager
import ufora.native.FORA as ForaNative
import ufora.FORA.TypedFora.TypedFora as TypedFora
import ufora.native.CallbackScheduler as CallbackScheduler
import time
import gc

PASS_COUNT = 10

class TestTypedForaCreateTuple(unittest.TestCase):
    def setUp(self):
        self.callbackScheduler = CallbackScheduler.singletonForTesting()

    def test_TypedFora_TupleGetItem(self):
        tupJovs = [
            ForaNative.parseStringToJOV("({String}, {String})"),
            ForaNative.parseStringToJOV("({String}, *)"),
            ForaNative.parseStringToJOV("({String}, 'a string 2')"),
            ForaNative.parseStringToJOV("('a string', 'a string 2')"),
            ForaNative.parseStringToJOV("('a string', *)"),
            ForaNative.parseStringToJOV("('a string', {String})"),
            ForaNative.parseStringToJOV("(*, 'a string 2')"),
            ForaNative.parseStringToJOV("(*, *)"),
            ForaNative.parseStringToJOV("(*, {String})")
            ]

        layoutStyles = [
            TypedFora.RefcountStyle.Pooled(),
            TypedFora.RefcountStyle.AsValueUnowned(),
            TypedFora.RefcountStyle.AsValueOwned()
            ]

        instance = ForaNative.ImplValContainer( ("a string", "a string 2") )

        for tupJov in tupJovs:
            for refcountStyle in layoutStyles:
                for index in range(2):
                    type = TypedFora.Type(tupJov, refcountStyle)

                    callable = self.generateTupleGetitemCallable(type, index)

                    def validator(result):
                        return result == instance[index]

                    self.runSimpleEvaluation(callable, [instance], validator)


    def test_TypedFora_CreateTuple(self):
        layoutStyles = [
            TypedFora.RefcountStyle.Pooled(),
            TypedFora.RefcountStyle.AsValueUnowned(),
            TypedFora.RefcountStyle.AsValueOwned()
            ]

        jovs = [
            ForaNative.parseStringToJOV("{String}"),
            ForaNative.parseStringToJOV("'a string'"),
            ForaNative.parseStringToJOV("*")
            ]

        aVal = ForaNative.ImplValContainer("a string")

        allLayouts = []

        for ls1 in layoutStyles:
            for jov1 in jovs:
                allLayouts.append(TypedFora.Type(jov1, ls1))

        for t1 in allLayouts:
            for t2 in allLayouts:
                callable = self.generateTupleCallable([t1, t2], [False, False])

                def validator(result):
                    return result == ForaNative.ImplValContainer((aVal, aVal))

                self.runSimpleEvaluation(callable, [aVal, aVal], validator)

    def runSimpleEvaluation(self, callable, arguments, validator):
        mainRuntime = Runtime.getMainRuntime()
        foraCompiler = mainRuntime.getTypedForaCompiler()
        jumpTarget = foraCompiler.compile(callable)

        while foraCompiler.anyCompilingOrPending():
            time.sleep(.01)

        gc.collect()

        for passIndex in range(PASS_COUNT):
            totalStringCount = ForaNative.totalStringCount()
            totalImplvalCount = ForaNative.totalImplvalCount()

            anExecutionContext = ExecutionContext.ExecutionContext(
                dataManager = VectorDataManager.constructVDM(self.callbackScheduler)
                )

            anExecutionContext.evaluateFunctionPointer(jumpTarget, *arguments)

            self.assertTrue(anExecutionContext.isFinished())

            res = anExecutionContext.getFinishedResult()

            self.assertTrue(validator(res.asResult.result),
                "invalid result in " + str(callable) + " with " + str(arguments) +
                ". got " + str(res)
                )

            res = None
            anExecutionContext.teardown()

            curRefs = (ForaNative.totalStringCount(), ForaNative.totalImplvalCount())

            self.assertEqual(
                (totalStringCount, totalImplvalCount),
                curRefs,
                "refcounts weren't maintained in " + str(callable) + " with " + str(arguments) +
                ". %s != %s" % (
                    (totalStringCount, totalImplvalCount),
                    curRefs
                    )
                )



    def generateTupleCallable(self, inputTypes, isTupleCallList):
        vars = []
        tupleArgs = []
        for ix in range(len(inputTypes)):
            type = inputTypes[ix]
            isTC = isTupleCallList[ix]

            vars.append(TypedFora.Variable.Temp(type))
            if isTupleCallList:
                tupleArgs.append(
                    TypedFora.MakeTupleArgument.TupleCall(
                        TypedFora.Expression.Var(vars[ix])
                        )
                    )
            else:
                tupleArgs.append(
                    TypedFora.MakeTupleArgument.Normal(
                        None,
                        TypedFora.Expression.Var(vars[ix])
                        )
                    )
        makeTupleExpression = TypedFora.Expression.MakeTuple(
                TypedFora.MakeTupleArgumentList(tupleArgs)
                )
        return TypedFora.Callable.SingleExpression(
            TypedFora.VariableList(vars),
            makeTupleExpression,
            makeTupleExpression.type(),
            False,
            False
            )

    def generateTupleGetitemCallable(self, tupleType, index):
        vars = [TypedFora.Variable.Temp(tupleType)]

        getItemExpression = TypedFora.Expression.GetItem(
                TypedFora.Expression.Var(vars[0]),
                index
                )
        return TypedFora.Callable.SingleExpression(
            TypedFora.VariableList(vars),
            getItemExpression,
            getItemExpression.type(),
            False,
            False
            )

