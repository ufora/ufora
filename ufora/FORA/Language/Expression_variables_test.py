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

import ufora.native.FORA as ForaNative

emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])

class ExpressionVariableBindingTest(unittest.TestCase):
    def parse(self, exprStr):
        e = ForaNative.parseStringToExpression(exprStr, emptyCodeDefinitionPoint, "")
        self.assertIsInstance(e, ForaNative.Expression, 'Parse error: ' + str(e))
        return e

    def testVars0(self):
        e = self.parse('')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, [])

    def testVars1(self):
        e = self.parse('x')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars2(self):
        e = self.parse('x = 1')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, ['x'])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars3(self):
        e = self.parse('( x )')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars4(self):
        e = self.parse('( x = 1 )')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, ['x'])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars5(self):
        e = self.parse('( let x = 0; x )')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars6(self):
        e = self.parse('( let x = 0; x = 1 )')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars7(self):
        e = self.parse('fun (x) { }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars8(self):
        e = self.parse('fun (x) { x }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars9(self):
        e = self.parse('fun (x) { x = 1 }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVars10(self):
        e = self.parse('fun (x) { x = 1; y }')
        self.assertEqual(e.freeVariables, ['y'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x', 'y'])

    def testVarsPull1(self):
        e = self.parse('pull i')
        self.assertEqual(e.freeVariables, ['i'])
        self.assertEqual(e.assignedVariables, ['i'])
        self.assertEqual(e.mentionedVariables, ['i'])

    def testVarsPull2(self):
        e = self.parse('( pull i )')
        self.assertEqual(e.freeVariables, ['i'])
        self.assertEqual(e.assignedVariables, ['i'])
        self.assertEqual(e.mentionedVariables, ['i'])

    def testVarsPull3(self):
        e = self.parse('( let i = nothing; pull i )')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['i'])

    def testVarsClass1(self):
        e = self.parse('class { a_member: x }')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClass2(self):
        e = self.parse('class { member x; a_member: x }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClass3(self):
        e = self.parse('class { member x; static a_member: x }')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClass4(self):
        e = self.parse('class { a_member: cls; a_member_2: self }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['cls', 'self'])

    def testVarsClass5(self):
        e = self.parse('class as cls_new self as self_new ' +
                '{ a_member: cls; a_member_2: self }')
        self.assertEqual(e.freeVariables, ['cls', 'self'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['cls', 'self'])

    def testPatterns1(self):
        e = self.parse('match () with (#A(x) or #B(y)) { x }')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x', 'y'])

    #check that 'mixins' are scoped outside of the object
    def testVarsObjectMixin(self):
        e = self.parse('object { x: 10; mixin x }')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClassMixin(self):
        e = self.parse('class { x: 10; mixin x }')
        self.assertEqual(e.freeVariables, ['x'])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClassMixin2(self):
        e = self.parse('class { static x: 10; mixin x }')
        self.assertEqual(e.freeVariables, [])
        self.assertEqual(e.assignedVariables, [])
        self.assertEqual(e.mentionedVariables, ['x'])

    def testVarsClassRebind(self):
        self.verifyRebind(
            'class { x: x; mixin x }',
            {'x':'y'},
            'class { x: x; mixin y }'
            )

    def testVarsClassRebind_2(self):
        self.verifyRebind(
            'class { z: x; mixin x }',
            {'x':'y'},
            'class { z: y; mixin y }'
            )

    def testVarsClassRebind_3(self):
        self.verifyRebind(
            'class { static x: x; mixin x }',
            {'x':'y'},
            'class { static x: x; mixin x }'
            )

    def testVarsClassRebind_4(self):
        self.verifyRebind(
            'class { static x: x; static mixin x }',
            {'x':'y'},
            'class { static x: x; static mixin y }'
            )

    def testVarsClassRebind_5(self):
        #verify static functions are bound within instance functions
        self.verifyRebind(
            'class { z: x; static x: fun(){} }',
            {'x':'y'},
            'class { z: x; static x: fun(){} }',
            )

    def testVarsClassRebind_6(self):
        self.verifyRebind(
            'class as K self as slf { x: x; mixin x }',
            {'x':'y'},
            'class as K self as slf { x: x; mixin y }'
            )

    def verifyRebind(self, src, rebindDict, dest):
        e = self.parse(src)
        eRebound = e.rebindFreeVariables(rebindDict)

        e2 = self.parse(dest)

        self.assertEqual(str(eRebound), str(e2),
            "After rebinding %s in %s, got %s instead of %s" % (
                rebindDict, src, str(eRebound), str(e2)
                )
            )

    def verifyRebindFreeVariableMemberAccess(self, src, rebindDict, dest):
        e = self.parse(src)
        eRebound = e
        for k, v in rebindDict.iteritems():
            eRebound = eRebound.rebindFreeVariableMemberAccess(k[0], k[1], v)

        e2 = self.parse(dest)

        self.assertEqual(
            str(eRebound), str(e2),
            "After rebinding %s in %s, got %s instead of %s" % (
                rebindDict, src, str(eRebound), str(e2)
                )
            )

    def testVariableAccessChains(self):
        e = self.parse('x.a.b.c')
        def toList(l):
            return [[str(y) for y in x] for x in l]

        self.assertEqual(toList(e.freeVariableMemberAccessChains), [['x','a','b','c']])

    def testVariableAccessChains2(self):
        e = self.parse('x.a.b.c; x.a')
        def toList(l):
            return [[str(y) for y in x] for x in l]

        self.assertEqual(toList(e.freeVariableMemberAccessChains), [['x','a'], ['x','a','b','c']])

    def testRebindingFreeVariableMemberAccesses(self):
        e = self.parse('f(x.a) + g(x.y.z)')

        e2 = e.rebindFreeVariableMemberAccess('x', 'a', 'x_a')
        e2 = e2.rebindFreeVariableMemberAccess('x', 'y', 'x_y')

        self.verifyRebindFreeVariableMemberAccess(
            'f(x.a) + g(x.y.z)',
            { ('x', 'a'): 'x_a', ('x', 'y'): 'x_y'},
            'f(x_a) + g(x_y.z)'
            )

    def testRebindingFreeVariableMemberAccessChains(self):
        e = self.parse('f(x.a) + g(x.y.z)')

        e2 = e.rebindFreeVariableMemberAccessChain(['x', 'y', 'z'], 'x_y_z')
        e2 = e2.rebindFreeVariableMemberAccessChain(['x', 'a'], 'x_a')
        e2 = e2.rebindFreeVariableMemberAccessChain(['f'], 'f2')

        self.assertEqual(
            str(e2),
            str(self.parse('f2(x_a) + g(x_y_z)'))
            )

