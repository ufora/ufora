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


class WrappingConstantConverterTest(unittest.TestCase):
    def setUp(self):
        self.converter = Converter.Converter(
            nativeConstantConverter=ForaNative.WrappingPythonConstantConverter(
                DefaultConverters.primitiveTypeMapping
                )
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

    def test_bools_1(self):
        pyValue = True
        implVal = self.convertPyObjectToImplVal(pyValue)
        foraValue = ForaValue.FORAValue(implVal).toPythonObject()
        self.assertEqual(self.converter.extractWrappedForaConstant(foraValue), pyValue)

    def test_strings_1(self):
        pyValue = "asdf"
        implVal = self.convertPyObjectToImplVal(pyValue)
        foraValue = ForaValue.FORAValue(implVal).toPythonObject()
        self.assertEqual(self.converter.extractWrappedForaConstant(foraValue), pyValue)

    def test_ints_1(self):
        pyValue = 1
        implVal = self.convertPyObjectToImplVal(pyValue)
        foraValue = ForaValue.FORAValue(implVal).toPythonObject()
        self.assertEqual(self.converter.extractWrappedForaConstant(foraValue), pyValue)

    def test_none_value(self):
        implVal = self.converter.nativeConstantConverter.noneValue()
        self.assertTrue('PyNone' in implVal.getClassName())
        self.assertTrue(implVal.getObjectLexicalMember('@m')[0].pyval is None)

    def test_WrappingConverter_ints_1(self):
        def f():
            x = 100
            return x

        res = ForaValue.FORAValue(self.convertPyObjectToImplVal(f))()

        self.assertEqual(self.converter.extractWrappedForaConstant(res), 100)

    def test_WrappingConverter_ints_2(self):
        def f():
            return 2 == 2

        res = ForaValue.FORAValue(self.convertPyObjectToImplVal(f))()

        self.assertEqual(self.converter.extractWrappedForaConstant(res), True)

    def test_WrappingConverter_strings_1(self):
        def f():
            x = "asdf"
            return x

        res = ForaValue.FORAValue(self.convertPyObjectToImplVal(f))()

        self.assertEqual(self.converter.extractWrappedForaConstant(res), "asdf")

