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

emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList(["dummy"])

class FunctionTest(unittest.TestCase):
    def parseStringToFunction(self, expr):
        expression = ForaNative.parseStringToExpression(expr, emptyCodeDefinitionPoint, "")
        return expression.extractRootLevelCreateFunctionPredicate()

    def parseStringToObject(self, expr):
        expression = ForaNative.parseStringToExpression(expr, emptyCodeDefinitionPoint, "")
        return expression.extractRootLevelCreateObjectPredicate()

    def testObjectSwitchStatements(self):
        #Check whether object member access is reduced to a simple switch statement,
        #instead of being a sequence of ifs.
        cfg1 = self.parseStringToObject("object {a:1} ").toCFG(3)
        cfg2 = self.parseStringToObject("object {a:1;b:2;c:3;d:4;e:5;f:6;g:7;h:8} ").toCFG(3)

        self.assertEqual(len(cfg1.subnodes), len(cfg2.subnodes))

