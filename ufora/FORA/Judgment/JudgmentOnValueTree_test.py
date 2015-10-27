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

class JudgmentOnValueTreeTest(unittest.TestCase):
    def testSimpleValues(self):
        self._testJOVTextSet([
                "1",
                "2",
                "... *"
                ],
            {
            "1":0,
            "2":1,
            "3":2,
            "2,4":2,
            "... *" : None
            }
            )

    def testSimpleTypes(self):
        self._testJOVTextSet(["{Int64}", "{Float64}", "{String}", "... *"],
            {
            "{Int64}": 0,
            "{Float64}": 1,
            "'astring'": 2
            }
            )

    def testSizings(self):
        self._testJOVTextSet(["*", "*,*", "*,*,*", "*,*,*, *, ... *"],
            {
            "1": 0,
            "1,1": 1,
            "1,1,1": 2,
            "1,1,1,1": 3,
            "1,1,1,1,1": 3
            }
            )


    def testJudgmentsAndSymbols(self):
        self._testJOVTextSet(["Int64", "`haro", "Float64"],
            {
            "Int64": 0,
            "`haro": 1,
            "Float64": 2
            }
            )

    def testTuples(self):
        self._testJOVTextSet(["(... *), `size", "(...*), {Symbol}", "*,`size"],
            {
            "(1,2,3), `size": 0,
            "(...*), `size": 0,
            "(...*), `haro": 1
            }
            )

    def testTypeMaps(self):
        self._testJOVTextSet([
                    "{Int32}",
                    "{Float64}",
                    "{String}",
                    "(*,*,*)",
                    "(...*)",
                    "*"
                    ],
            {
            "(1,2,3)" : 3,
            "(*,*,*)" : 3,
            "(*,*)": 4
            }
            )

    def _testJOVTextSet(self, jovStrings, jovMappings):
        jovts = [ForaNative.parseStringToJOVT(x) for x in jovStrings]
        tree = ForaNative.JudgmentOnValueTree(jovts)

        for jmtString, targetIx in jovMappings.iteritems():
            testJovt = ForaNative.parseStringToJOVT(jmtString)
            searchedIx = tree.searchForJOVT(testJovt)
            self.assertEqual(targetIx, searchedIx,
                "JOV Tree:\n%s\nError: %s mapped to %s instead of %s" % (
                    str(tree),
                    str(testJovt),
                    searchedIx,
                    targetIx
                    ))

