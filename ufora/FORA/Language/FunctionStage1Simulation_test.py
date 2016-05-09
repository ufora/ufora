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

import ufora.FORA.python.FORA as FORA

import ufora.native.FORA as ForaNative

import unittest

def makeSymbolIvc(symbolString):
    return ForaNative.ImplValContainer(
        ForaNative.makeSymbol(
            symbolString
            )
        )

class FunctionStage1SimulationTest(unittest.TestCase):

    def setUp(self):
        self.Symbol_call = makeSymbolIvc("Call")
        self.Symbol_member = makeSymbolIvc("Member")


    def test_simulateGetItem(self):
        n = 42

        ivc = FORA.eval("object { m: %s }" % n).implVal_

        res = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (ivc, self.Symbol_member, makeSymbolIvc("m"))
                )
            )

        self.assertEqual(res, ForaNative.ImplValContainer(n))

    def test_unbind(self):
        ivc = FORA.eval(
            """let m = \"asdf\";
               let C = class {
                   member x;
                   member y;
                   f: fun() { m };
                   };
               let c = C(1,2);
               c"""
            ).implVal_

        res = makeSymbolIvc("Unbind").simulateCall(
            ForaNative.ImplValContainer(
                (ivc,)
                )
            )

        self.assertIsNotNone(res)

        self.assertEqual(len(res), 4)

    def test_pattern_matching(self):
        ivc = FORA.eval(
            """let o = object {
                   ...(`Member, `x) { 1 };
                   y: 2;
                   ...(`Member, `z) { 3 };
                   };
               o"""
            ).implVal_

        def sim(memberName):
            return ForaNative.simulateApply(
                ForaNative.ImplValContainer(
                    (ivc, makeSymbolIvc("Member"),
                        makeSymbolIvc(memberName))
                    )
                ).pyval

        self.assertEqual(sim("x"), 1)
        self.assertEqual(sim("y"), 2)
        self.assertEqual(sim("z"), 3)

    def test_createInstance_1(self):
        classIvc = FORA.eval(
            """let C = class {
                   member x;
                   member y;
                   };
               C"""
            ).implVal_

        x = 1
        y = 2

        res = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (classIvc, makeSymbolIvc("CreateInstance"),
                 ForaNative.ImplValContainer(x), ForaNative.ImplValContainer(y)
                 )
            )
        )

        self.assertIsNotNone(res)

        computed_x = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (res, self.Symbol_member, makeSymbolIvc("x"))
                )
            )

        self.assertEqual(computed_x, ForaNative.ImplValContainer(x))

    def test_createInstance_2(self):
        classIvc = FORA.eval(
            """let C = class {
                   member y;
                   member x;
                   };
               C"""
            ).implVal_

        x = 1
        y = 2

        res = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (classIvc, makeSymbolIvc("CreateInstance"),
                 ForaNative.ImplValContainer(y), ForaNative.ImplValContainer(x)
                 )
            )
        )

        self.assertIsNotNone(res)

        computed_x = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (res, self.Symbol_member, makeSymbolIvc("x"))
                )
            )

        self.assertEqual(computed_x, ForaNative.ImplValContainer(x))

