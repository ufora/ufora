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
import pyfora.ObjectVisitors as ObjectVisitors
import pyfora.DefaultPureImplementationMappings as DefaultPureImplementationMappings

import unittest


class InstanceConversion(unittest.TestCase):
    def setUp(self):
        self.converter = Converter.Converter(
            nativeListConverter=DefaultConverters.defaultWrappingNativeListConverter,
            nativeConstantConverter=ForaNative.WrappingPythonConstantConverter(
                DefaultConverters.primitiveTypeMapping
                ),
            vdmOverride=ForaValue.evaluator().getVDM(),
            purePythonModuleImplVal=DefaultConverters.builtinPythonImplVal
            )
        self.objectRegistry = ObjectRegistry.ObjectRegistry()
        self.purePythonImplementations = DefaultPureImplementationMappings.getMappings()

    def convertPyObjectToImplVal(self, pyObject):
        objectId = ObjectVisitors.walkPythonObject(
            pyObject,
            self.objectRegistry,
            self.purePythonImplementations
            )

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
                functionForaValue()
                )
        else:
            for valueToCheck in valuesToCheck:
                self.assertEqual(
                    pyFunction(valueToCheck),
                    functionForaValue(valueToCheck)
                    )

    def test_len_1(self):
        class ThingWithLen:
            def __init__(self, len):
                self.len = len
            def __len__(self):
                return self.len

        def pyFun(x):
            return len(x)

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyFun)
            )

        thingWithLen = ThingWithLen(100)

        foraThingWithLen = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithLen)
            )

        # in converter, we're using PyInts as len
        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithLen)),
            pyFun(thingWithLen)
            )

    def test_len_2(self):
        def pyFun(x):
            return len(x)

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyFun)
            )

        thingWithLen = [1,2,3]

        foraThingWithLen = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithLen)
            )

        # in converter, we're using PyInts as len
        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithLen)),
            pyFun(thingWithLen)
            )

    def test_len_3(self):
        def lenFun(x):
            return len(x)

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(lenFun)
            )

        thingWithLen = "asdf"
        foraThingWithLen = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithLen)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithLen)),
            lenFun(thingWithLen)
            )

    def test_len_4(self):
        thingWithLen = "asdf"
        foraThingWithLen = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithLen)
            )

        foraLen = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(len)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraLen(foraThingWithLen)),
            len(thingWithLen)
            )

    def test_str_1(self):
        class ThingWithStr:
            def __init__(self, str):
                self.str = str
            def __str__(self):
                return self.str

        def pyFun(x):
            return str(x)

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(pyFun)
            )

        thingWithStr = ThingWithStr("100")

        foraThingWithStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithStr)
            )

        # in converter, we're using PyStrs
        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithStr)),
            pyFun(thingWithStr)
            )

    def test_str_2(self):
        def strFun(x):
            return str(x)

        thingWithStr = 42
        foraThingWithStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithStr)
            )

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(strFun)
            )

        self.assertEqual(
            strFun(thingWithStr),
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithStr))
            )

    def test_str_3(self):
        def strFun(x):
            return str(x)

        thingWithStr = "asdf"
        foraThingWithStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithStr)
            )

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(strFun)
            )

        self.assertEqual(
            strFun(thingWithStr),
            self.converter.extractWrappedForaConstant(foraFun(foraThingWithStr))
            )

    def test_str_4(self):
        thingWithStr = "asdf"
        foraThingWithStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(thingWithStr)
            )

        foraStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(str)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraStr(foraThingWithStr)),
            str(thingWithStr)
            )

    def test_None_1(self):
        def noneFun():
            return str(None)

        foraFun = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(noneFun)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraFun()),
            noneFun()
            )

    def test_None_2(self):
        foraNone = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(None)
            )
        foraStr = ForaValue.FORAValue(
            self.convertPyObjectToImplVal(str)
            )

        self.assertEqual(
            self.converter.extractWrappedForaConstant(foraStr(foraNone)),
            str(None)
            )

