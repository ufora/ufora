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
import ufora.FORA.python.FORA as Fora
import ufora.FORA.FORAValuePrinting.FORAValuePrinter_test as ForaValuePrintingTest
from ufora.FORA.python.ParseException import ParseException

# known bug: the whitespace inserter messes up triple quotes (doesn't indent properly)
def generateTestExpressions():
    def isOk(s):
        return '"""' not in s and "'''" not in s

    testFunctions = ForaValuePrintingTest.generateTestFunctions()
    reprSymbol = Fora.makeSymbol("ParsableRepresentation")
    tr = [reprSymbol(testFun) for testFun in testFunctions]

    return [x for x in tr if isOk(x)]

class ParserTest(unittest.TestCase):
    def setUp(self):
        self.whitespaceInserter = ForaNative.RandomWhitespaceInserter(42)

    def assertValidParse(self, foraExpressionText):
        result = ForaNative.parseStringToExpression(
            foraExpressionText,
            ForaNative.CodeDefinitionPoint.ExternalFromStringList([]),
            ""
            )
        self.assertTrue(isinstance(result, ForaNative.Expression),
            "'%s' didn't parse: %s" % (foraExpressionText, result)
            )

    def assertInvalidParse(self, foraExpressionText):
        result = ForaNative.parseStringToExpression(
            foraExpressionText,
            ForaNative.CodeDefinitionPoint.ExternalFromStringList([]),
            ""
            )
        self.assertTrue(isinstance(result, ForaNative.FunctionParseError),
            "'%s' parsed and shouldn't have" % foraExpressionText
            )

    def test_basic_parsing(self):
        self.assertValidParse("1")
        self.assertValidParse("1.0")
        self.assertValidParse("1.0f32")
        self.assertValidParse("1s32")
        self.assertValidParse("1u32")

        self.assertValidParse("'strings'")
        self.assertValidParse("`symbols")

        self.assertInvalidParse(")")
        self.assertInvalidParse("(]")

        self.assertInvalidParse("fun()")
        self.assertValidParse("fun() {}")

    def test_pattern_parsing(self):
        #Verify that parser only accepts valid patterns
        self.assertValidParse("fun(x) {}")
        self.assertValidParse("fun(*x) {}")
        self.assertValidParse("fun(x,*y,z) {}")
        self.assertInvalidParse("fun(x,*y,*z) {}")

        self.assertValidParse("fun(x=1) {}")
        self.assertValidParse("fun(x=1,y=2) {}")
        self.assertValidParse("fun(x=1,*args,y=2) {}")

        self.assertValidParse("fun(a, x=1) {}")
        self.assertValidParse("fun(a, x=1,y=2, b) {}")
        self.assertValidParse("fun(a1, a2, a3=1,a4=3,*args,a5=2, a6, a7, a8) {}")

        self.assertInvalidParse("fun(a1, a2=2, a3, a4=3) {}")

    def testClassBinding(self):
        self.assertInvalidParse("class { member x; x: 10 }")
        self.assertInvalidParse("class { member x; static x: 10 }")
        self.assertInvalidParse("class { x: 20; static x: 10 }")

    # def test_parsing_big_but_not_too_big_vectors_doesnt_fail_1(self):
    #     sz = 50000
    #     s = "["
    #     for i in range(sz - 1):
    #         s = s + "0, "
    #     s = s + "0] == Vector.uniform(%s, 0)" % sz
    #     self.assertTrue(Fora.eval(s))

    # def test_parsing_big_but_not_too_big_vectors_doesnt_fail_2(self):
    #     sz = 100000
    #     s = "["
    #     for i in range(sz - 1):
    #         s = s + "%s, " % i
    #     s = s + "%s] == Vector.range(%s)" %(sz - 1, sz)
    #     self.assertTrue(Fora.eval(s))

    def test_deep_parse_trees_trigger_ParseErrors(self):
        sz = 1000
        s = "0 + "
        for i in range(sz - 1):
            s = s + "1 + "
        s = s + "1"
        try:
            Fora.eval(s)
            self.assertTrue(False)
        except ParseException:
            self.assertTrue(True)

    def parseStringToExpression(self, string):
        return ForaNative.parseStringToExpression(
            string,
            ForaNative.CodeDefinitionPoint(),
            "<eval>"
            )

    def insertRandomWhitespace(self, string):
        simpleParse = ForaNative.SimpleParseNode.parse(string)
        return \
            self.whitespaceInserter.stringifyWithRandomWhitespaceAndComments(
            simpleParse
            )

    def assertInsensitivityToWhitespace(self, exprStr):
        expr1 = self.parseStringToExpression(exprStr)

        for ix in xrange(25):
            exprStrWithWhitespace = self.insertRandomWhitespace(exprStr)

            expr2 = self.parseStringToExpression(exprStrWithWhitespace)

            self.assertEqual(
                expr1, expr2, "expressions did not parse equally!\n" +
                str(exprStr) + "\n\nvs\n\n" + str(exprStrWithWhitespace) +
                "\nresults: expr1 = " + str(expr1) + "\n\nvs\n\nexpr2 = " + str(expr2)
                )

    def test_insensitivityToWhitespace(self):
        testExprs = generateTestExpressions()
        for testExpr in testExprs:
            self.assertInsensitivityToWhitespace(testExpr)

