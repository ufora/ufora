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
import ufora.FORA.python.CacheSemantics as CacheSemantics


class CacheSemanticsTest(unittest.TestCase):
    def test_chunking(self):
        self.assertEqual(
            CacheSemantics.getAppropriateChunksForSize(0,50),
            []
            )

        self.assertEqual(
            CacheSemantics.getAppropriateChunksForSize(100,50),
            [(0,50),(50,100)]
            )

        self.assertEqual(
            CacheSemantics.getAppropriateChunksForSize(120,50),
            [(0,50),(50,120)]
            )

        self.assertEqual(
            CacheSemantics.getAppropriateChunksForSize(130,50),
            [(0,50),(50,100),(100,130)]
            )

