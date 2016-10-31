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

import ufora.native.FORA as FORANative
import ufora.FORA.python.FORA as FORA

ivc = FORANative.ImplValContainer
sym = FORANative.makeSymbol
tag = FORANative.makeTag

class TestImplValContainer(unittest.TestCase):
    def test_typeCategory(self):
        self.assertEqual(ivc(1).typeCategory, "Integer")
        self.assertEqual(ivc("1").typeCategory, "String")
        self.assertEqual(ivc({}).typeCategory, "Dictionary")

    def test_stringization(self):
        self.assertEqual(str(ivc("asdf")), '"asdf"')
        self.assertEqual(str(ivc(1)), "1")
        self.assertEqual(str(ivc(1.0)), "1.0")
        self.assertEqual(str(sym("asdf")), "`asdf")
        self.assertEqual(str(tag("asdf")), "#asdf")
        self.assertEqual(str(ivc((1,2))), "(1, 2)")

    def test_extraction(self):
        self.assertEqual(ivc((1,2,3)).pyval, (1,2,3))

    def test_dictionaryInterface(self):
        d = ivc({1:2, 3:"b"})
        self.assertTrue(d.isDictionary())
        self.assertTrue(len(d) == 2)

        dAsTuples = sorted([x for x in d])

        self.assertEqual(dAsTuples[0], (ivc(1),ivc(2)))
        self.assertEqual(dAsTuples[1], (ivc(3),ivc("b")))

    def test_stringInterface(self):
        s = ivc("a string")
        self.assertTrue(s.isString())
        self.assertTrue(len(s) == len("a string"))

        self.assertEqual("".join(list(s)), "a string")

    def test_iteration(self):
        x = 0
        for z in ivc((1,2,3)):
            x = x + z.pyval

        self.assertEqual(x, 6)

    def test_getObjectDefinitionTermsWithMetadata_1(self):
        obj = FORA.extractImplValContainer(
            FORA.eval('object { "x!!!" x: 10; "operator+!!" operator +(other) { 10 }; "F!" f: fun(){}; g: fun(){} };')
            )
        objTermsWithMeta = obj.getObjectDefinitionTermsWithMetadata()

        #TODO have a better test here
        self.assertEqual(len(objTermsWithMeta), 4)

    def test_getObjectDefinitionTermsWithMetadata_2(self):
        obj = FORA.extractImplValContainer(
            FORA.eval('class { "x!" member x; "new!" operator new() {}; "F!" f: fun() {}; "static!" static g: "inner" fun(){}; "operator+" operator+(){}; }')
            )
        objTermsWithMeta = obj.getObjectDefinitionTermsWithMetadata()

        #TODO have a better test here
        self.assertEqual(len(objTermsWithMeta), 5)

    def memberFromString(self, foraText, member):
        obj = FORA.extractImplValContainer(FORA.eval(foraText))
        res = obj.getObjectMember(member)

        if res is None:
            return None

        return FORA.ForaValue.FORAValue(res).toPythonObject()

    def test_getObjectMember_1(self):
        self.assertEqual(self.memberFromString("object { x: 10 }", 'x'), 10)

    def test_getObjectMember_2(self):
        obj = FORA.extractImplValContainer(
            FORA.eval("object { x: 1+2 }")
            )
        self.assertEqual(obj.getObjectMember('x'), None)

    def test_getObjectMember_3(self):
        obj = FORA.extractImplValContainer(
            FORA.eval("object { x: object { y: 20 } }")
            )
        obj2 = obj.getObjectMember('x')

        self.assertEqual(obj2.getObjectMember('y').pyval, 20)

    def test_getObjectMember_4(self):
        obj = FORA.extractImplValContainer(
            FORA.eval("object { x: fun () { } }")
            )
        obj2 = obj.getObjectMember('x')

        self.assertTrue(obj2 is not None)

    def test_getObjectMember_5(self):
        obj2 = self.memberFromString("object { x: object { q: y }; y: 10 }", 'x')

        self.assertTrue(obj2 is not None)
        self.assertTrue(obj2.q == 10)

    def test_getObjectMember_6(self):
        obj2 = self.memberFromString("object { x: fun() { y }; y: 10 }", 'x')

        self.assertTrue(obj2 is not None)
        self.assertTrue(obj2() == 10)

    def test_getObjectMember_7(self):
        obj2 = self.memberFromString("object { x: object { q: y; n: q; }; y: 10 }", 'x')

        self.assertTrue(obj2 is not None)
        self.assertTrue(obj2.q == 10)

    def test_getObjectMember_8(self):
        member = self.memberFromString("object { x: class { member z; static result: y }; y: 10 }", 'x')
        self.assertTrue(member is not None)
        self.assertTrue(member.result == 10)

    def test_getObjectMember_9(self):
        member = self.memberFromString("let z = object {  }; object { mixin z; x: fun(){y}; y: 10 }", 'x')
        self.assertTrue(member is not None)
        self.assertTrue(member() == 10)

    def test_getObjectMember_10(self):
        member = self.memberFromString("let z = object { x: fun(){self.y} }; object { mixin z; y: 10 }", 'x')
        self.assertTrue(member is not None)
        self.assertTrue(member() == 10)

    def test_getObjectMember_recursive(self):
        member = self.memberFromString("object { x: self.x }", 'x')
        self.assertTrue(member is None)

    def test_vectorSlicing(self):
        obj = FORA.extractImplValContainer(
                FORA.eval("Vector.range(20)[3,-2,2]")
                )
        self.assertEqual(obj[0], ivc(3))
        self.assertEqual(obj[1], ivc(5))
        self.assertEqual(len(obj), 8)
        self.assertEqual(obj[-1], ivc(17))

        with self.assertRaises(IndexError):
            obj[8]

    def test_getDataMembers_1(self):
        classIvc = FORA.eval(
            """let C = class {
                   member x;
                   member y;
                   member z;
                   };
               C"""
            ).implVal_

        self.assertEqual(
            [str(val) for val in classIvc.getDataMembers],
            ["x", "y", "z"]
            )

    def test_getDataMembers_2(self):
        classIvc = FORA.eval(
            """let C = class {
                   member y;
                   member x;
                   member z;
                   };
               C"""
            ).implVal_

        self.assertEqual(
            [str(val) for val in classIvc.getDataMembers],
            ["y", "x", "z"]
            )

    def test_getDataMembers_3(self):
        classIvc = FORA.eval(
            """let C = class {
                   member z;
                   member y;
                   member x;
                   };
               C"""
            ).implVal_

        self.assertEqual(
            [str(val) for val in classIvc.getDataMembers],
            ["z", "y", "x"]
            )

