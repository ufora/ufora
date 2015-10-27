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

import ufora.FORA.python.PurePython.Converter as Converter
import ufora.FORA.python.PurePython.DefaultConverters as DefaultConverters
import ufora.FORA.python.ForaValue as ForaValue

import ufora.native.FORA as ForaNative

import pyfora.ObjectRegistry as ObjectRegistry

from pyfora.ObjectVisitors import walkPythonObject

import unittest


class WrappingConstantWrappingListConverterTest(unittest.TestCase):
    def setUp(self):
        self.converter = Converter.Converter(
            nativeConstantConverter=ForaNative.WrappingPythonConstantConverter(
                DefaultConverters.primitiveTypeMapping
                ),
            nativeListConverter=DefaultConverters.defaultWrappingNativeListConverter,
            nativeTupleConverter=DefaultConverters.defaultWrappingNativeTupleConverter,
            vdmOverride=ForaValue.evaluator().getVDM()
            )
        self.objectRegistry = ObjectRegistry.ObjectRegistry()

    def convertPyObjectToImplVal(self, pyObject):
        objectId = walkPythonObject(pyObject, self.objectRegistry)

        implVal = [None]
        def onResult(result):
            if isinstance(result, Exception):
                raise result
            else:
                implVal[0] = result

        self.converter.convert(objectId, self.objectRegistry, onResult)
        return implVal[0]


    def checkFunctionEquivalence(self, pyFunction, valuesToCheck=None):
        functionImplVal = self.convertPyObjectToImplVal(pyFunction)

        self.assertIsInstance(functionImplVal, ForaNative.ImplValContainer)

        functionForaValue = ForaValue.FORAValue(functionImplVal)

        if valuesToCheck is None:
            self.assertEqual(
                pyFunction(),
                self.converter.extractWrappedForaConstant(functionForaValue())
                )
        else:
            for valueToCheck in valuesToCheck:
                self.assertEqual(
                    pyFunction(valueToCheck),
                    self.converter.extractWrappedForaConstant(functionForaValue(valueToCheck))
                    )

    def test_pyLists_1(self):
        x = [1,2,3]

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(x)
            )

        for ix in range(-3,3):
            self.assertEqual(
                self.converter.extractWrappedForaConstant(foraValue[ix]),
                x[ix]
                )

    def test_pyLists_4(self):
        v = [1,2,3]

        foraList = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(v)
            )

        self.assertEqual(
            v[0],
            self.converter.extractWrappedForaConstant(foraList[0])
            )

    def test_pyLists_5(self):
        v = [1,2,3]
        def f(ix):
            return v[ix]

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        for arg in range(-3, 3):
            self.assertEqual(
                self.converter.extractWrappedForaConstant(foraValue(arg)),
                f(arg)
                )

    def test_pyLists_7(self):
        v = [1,2,3]

        foraList = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(v)
            )

        for ix in range(-3, 3):
            self.assertEqual(
                v[ix],
                self.converter.extractWrappedForaConstant(foraList[ix])
                )

    def test_pyLists_8(self):
        v = [1,2,3]

        foraList = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(v)
            )

        for ix in range(-3, 3):
            self.assertEqual(
                v[ix],
                self.converter.extractWrappedForaConstant(foraList[ix])
                )

    def test_nestedLists_2(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.checkFunctionEquivalence(nestedLists)

    def test_inStatement_1(self):
        def inStatement():
            x = [0,1,2,3]
            return 0 in x

        foraFunction = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(inStatement)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFunction()),
            inStatement()
            )

    def test_iteration_1(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.checkFunctionEquivalence(iteration_1)

    def test_nestedComprehensions_1(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.checkFunctionEquivalence(nestedComprehensions)

    def test_listComprehensions_1(self):
        def listComprehensions_1():
            aList = [0,1,2,3]
            aList = [elt ** 2 for elt in aList]
            return aList[-1]

        self.checkFunctionEquivalence(listComprehensions_1)

    def test_listComprehensions_3(self):
        def listComprehensions_3():
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[1][0]

        self.checkFunctionEquivalence(listComprehensions_3)

    def test_basicLists_1(self):
        def basicLists(x):
            aList = [x] + [x]
            return aList[0] + aList[1]

        foraValueFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(basicLists)
            )

        for pyArg in range(4):
            foraValueArg = ForaValue.FORAValue(
                self.convertPyObjectToImplVal(pyArg)
                )
            self.assertEqual(
                basicLists(pyArg),
                self.converter.extractWrappedForaConstant(foraValueFun(foraValueArg))
                )

    def test_pyTuples_1(self):
        def f(ix):
            t = (1,2,3)
            return t[ix]

        foraValue = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(f)
            )

        for ix in range(-3, 3):
            self.assertEqual(
                self.converter.extractWrappedForaConstant(foraValue(ix)),
                f(ix)
                )

    def test_pyTuples_2(self):
        t = (1,2,3)

        foraTuple = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(t)
            )

        for ix in range(-3, 3):
            self.assertEqual(
                t[ix],
                self.converter.extractWrappedForaConstant(foraTuple[ix])
                )








