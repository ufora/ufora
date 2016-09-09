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

class TestSimpleParse(unittest.TestCase):
    #Test cases to verify that we can't accidentally wrap something in {}'s if they don't
    #parse as a module member and then get screwy results. Expressions like 'x:10' shouldn't
    #be considered valid expressions.

    def assertValidParseRange(self, node, text):
        subtext = text[node.extent.start.rawOffset:node.extent.stop.rawOffset]
        try:
            simpleParse = ForaNative.SimpleParseNode.parse(subtext)
        except:
            self.assertTrue(False,
                "couldn't parse text for node %s which was '%s'" % (node, subtext)
                )
            return

        self.assertEqual(str(simpleParse), str(node),
            "node didn't parse to itself: %s (%s) != %s" %
                (node, subtext, simpleParse)
            )

    def walkNodesAndTestExtents(self, node, text):
        self.assertValidParseRange(node, text)
        if node.isGrouping():
            self.walkNodesAndTestExtents(node.asGrouping.node, text)
        elif node.isSequence():
            for n in node.asSequence.nodes:
                self.walkNodesAndTestExtents(n, text)


    def testMultilineString(self):
        def test(source, target):
            sp = ForaNative.SimpleParseNode.parse(source)
            self.assertTrue(sp.isQuote())
            self.assertEqual(sp.asQuote.val, target)

        test("'''asdf\nasdf\nasdf'''", "asdf\nasdf\nasdf")
        test("\t\t'''asdf\n\t\tasdf\n\t\tasdf'''", "asdf\nasdf\nasdf")
        test("\n\n\t\t'''asdf\n\t\tasdf\n\t\tasdf'''", "asdf\nasdf\nasdf")
        test("\t'''asdf\n\tasdf\n\n\n\tasdf'''", "asdf\nasdf\n\n\nasdf")
        test("\t'''asdf\n\tasdf\na\n\n\tasdf'''", "asdf\n\tasdf\na\n\n\tasdf")


    def testExtents(self):
        toTest = ["x: 10", "x,10", "x; 10", "( a )", "()"]
        toTest += ["""(position:(7, 2), height:3, down:"n")
                        id_02262e745b84487792d8094c7d910de7:   "parameters:";

                        (height:3, down:"daily_vol")
                        n:    10000;

                        (height:3, down:"lower_barrier")
                        daily_vol:    .02;

                        (width:41, height:3)
                        lower_barrier:    .9;

                        (position:(67, 2), width:41, height:3)
                        id_e1c3ae8528a74b6a8084695de6f1dc42:   "pricing functions";

                        (position:(67, 8), height:3, down:"cashflows_once")
                        price_once:    fun(stock_price_process, option) {
                                  let state = option.initialState;
                                  let t = 0;
                                  let pnl = 0.0;

                                  for price in stock_price_process {
                                    match (option.cashflowAndNextState(price, t, state)) with
                                      (nothing) { return pnl; }
                                      ((cashflow, nextState)) {
                                        pnl = pnl + cashflow;
                                        state = nextState;
                                        };
                                    t = t + 1
                                    }
                                  }
                                  ;
                        """]

        for text in toTest:
            self.walkNodesAndTestExtents(ForaNative.SimpleParseNode.parse(text), text)

