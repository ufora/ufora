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

import pyfora.StronglyConnectedComponents as StronglyConnectedComponents

import unittest

class StronglyConnecteComponentsTest(unittest.TestCase):
    def test_stronglyConnectedComponents_1(self):
        graph = {
            0: [1, 2],
            1: [0, 2],
            2: []
            }
        scc = StronglyConnectedComponents.stronglyConnectedComponents(graph)
        self.assertEqual(
            scc,
            [(2,), (1, 0)]
            )

    def test_stronglyConnectedComponents_2(self):
        graph = {
            0: [4],
            1: [0],
            2: [1, 3],
            3: [2],
            4: [1],
            5: [4, 1, 6],
            6: [5, 2],
            7: [6, 7]
            }
        scc = StronglyConnectedComponents.stronglyConnectedComponents(graph)
        self.assertEqual(
            scc,
            [(1, 4, 0), (3, 2), (6, 5), (7,)]
            )

if __name__ == "__main__":
    unittest.main()

