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
import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Expression as Expression
import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.ParseException as ParseException
import ufora.native.FORA as FORANative
import ufora.native.Hash as HashNative

class TestFORA(unittest.TestCase):
    def setUp(self):
        pass

    def assertFreeVarsAre(self, toParse, freeVars):
        """assert that if you parse 'toParse', it has free variables 'freeVars'"""
        defPoint = FORANative.CodeDefinitionPoint.ExternalFromStringList([])
        expr = Expression.Expression.parse(toParse, defPoint)
        self.assertEqual(expr.freeVariables, freeVars)
        for f in freeVars:
            self.assertTrue(expr.freeVariableUsePoints(f),
                toParse + " had variable %s free but no use points" % f
                )


    def assertAssignedVarsAre(self, toParse, assigned):
        """assert that if you parse 'toParse', it has free variables 'freeVars'"""
        defPoint = FORANative.CodeDefinitionPoint.ExternalFromStringList([])
        expr = Expression.Expression.parse(toParse, defPoint)
        self.assertEqual(expr.assignedVariables, assigned)
        for a in assigned:
            self.assertTrue(expr.assignedVariableUsePoints(a),
                toParse + " had assigned variable %s but no use points" % a
                )


    def test_freeVariablesInClosure(self):
        self.assertFreeVarsAre("fun() { x }", ['x'])
        self.assertAssignedVarsAre("fun() { x }", [])

    def test_freeVariablesInAssignment(self):
        self.assertFreeVarsAre("(x = 10,)", ['x'])
        self.assertAssignedVarsAre("(x = 10,)", ['x'])

    def test_freeVariables(self):
        self.assertFreeVarsAre("(x,y)", ['x','y'])
        self.assertAssignedVarsAre("(x,y)", [])

    def test_recursiveLetGeneratesParseError(self):
        with self.assertRaises(ParseException.ParseException):
            FORA.eval("let x = x", locals = {})

    def test_nonRecursiveLetOK(self):
        self.assertEqual(FORA.eval("let x = y, y = 1; x", locals = {}), 1)

    def test_assignedButNotFreeIsParseError(self):
        with self.assertRaises(ParseException.ParseException):
            FORA.eval("fun() { x = 10 }", locals = {})

    def test_throwsIfNotCreateNewLocals(self):
        with self.assertRaises(ParseException.ParseException):
            FORA.eval("(x = 10,)", locals = {})

    def test_returnCausesRaise(self):
        with self.assertRaises(ParseException.ParseException):
            FORA.eval("return 10")

    def test_ForaExceptions_1(self):
        with self.assertRaises(ForaValue.FORAException):
            FORA.eval("1 / 0")

    def test_let_bindings(self):
        locals = {}
        FORA.eval("let x = 10", locals)
        self.assertEqual(locals, {'x':10})

    def test_let_bindings_2(self):
        locals = {}
        FORA.eval("let x = 10; x = 20", locals)
        self.assertEqual(locals, {'x':20})

    def test_throwUpdatesVariables(self):
        locals = {}
        try:
            FORA.eval("let x = 10; throw 20", locals)
            self.assertTrue(False)
        except ForaValue.FORAException as e:
            self.assertEqual(e.foraVal, 20)
            self.assertTrue(e.trace is not None)
            self.assertTrue(isinstance(e.trace, list))
            for l in e.trace:
                assert isinstance(l, HashNative.Hash)

        self.assertEqual(locals, {'x':10})

    def test_throwProducesStacktraces_1(self):
        try:
            FORA.eval("let x = 10; throw 20")
        except ForaValue.FORAException as e:
            self.assertTrue(e.trace is not None)

    def test_throwProducesStacktraces_2(self):
        try:
            FORA.eval("let x = 10; throw 20")
        except ForaValue.FORAException as e:
            self.assertTrue(e.trace is not None)

