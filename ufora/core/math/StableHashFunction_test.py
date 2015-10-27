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
import ufora.core.math.StableHashFunction as StableHashFunction

class TestStableHashFunction(unittest.TestCase):
    def test_tuples(self):
        t1 = (1,2,3)
        t2 = (1,2,3)
        self.assertTrue(t1 is not t2)

        self.assertEqual(
            StableHashFunction.stableShaHashForObject(t1, True),
            StableHashFunction.stableShaHashForObject(t2, True)
            )

    def test_tuples_2(self):
        t1 = ("a", unicode("s"), type(10))
        t2 = ("a", unicode("s"), type(10))
        t3 = ("b", unicode("s"), type(10))

        self.assertTrue(t1 is not t2)

        self.assertEqual(
            StableHashFunction.stableShaHashForObject(t1, True),
            StableHashFunction.stableShaHashForObject(t2, True)
            )
        self.assertNotEqual(
            StableHashFunction.stableShaHashForObject(t1, True),
            StableHashFunction.stableShaHashForObject(t3, True)
            )

