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

import ufora.native.core as NativeCore

class TestMapWithIndex(unittest.TestCase):
    def test_getKeys(self):
        mapWithIndex = NativeCore.MapWithIndex()

        mapWithIndex.set(1,2)
        mapWithIndex.set(2,2)

        self.assertEqual(mapWithIndex.getKeys(2), [1,2])

        mapWithIndex.set(2,3)

        self.assertEqual(mapWithIndex.getKeys(2), [1])

        mapWithIndex.set(2,2)
        mapWithIndex.set(3,2)

        self.assertEqual(mapWithIndex.getKeys(2), [1,2,3])

        self.assertEqual(mapWithIndex.highestKey(), 3)
        self.assertEqual(mapWithIndex.highestValue(), 2)

        self.assertEqual(mapWithIndex.lowestKey(), 1)
        self.assertEqual(mapWithIndex.lowestValue(), 2)

        keys = [mapWithIndex.lowestKey()]
        while mapWithIndex.nextKey(keys[-1]) is not None:
            keys.append(mapWithIndex.nextKey(keys[-1]))
        self.assertEqual(keys,[1,2,3])

        mapWithIndex.set(3,3)

        values = [mapWithIndex.lowestValue()]
        while mapWithIndex.nextValue(values[-1]) is not None:
            values.append(mapWithIndex.nextValue(values[-1]))
        self.assertEqual(values,[2,3])


    def test_keyIteration(self):
        x = NativeCore.MapWithIndex()
        x[0.0] = 1
        x[1.0] = 1
        x[2.0] = 1

        self.assertEqual(x.nextKey(-0.5), 0.0)
        self.assertEqual(x.nextKey(0.0), 1.0)
        self.assertEqual(x.nextKey(0.5), 1.0)
        self.assertEqual(x.nextKey(1.0), 2.0)
        self.assertEqual(x.nextKey(1.5), 2.0)
        self.assertEqual(x.nextKey(2.0), None)
        self.assertEqual(x.nextKey(2.5), None)

        self.assertEqual(x.prevKey(-0.5), None)
        self.assertEqual(x.prevKey(0.0), None)
        self.assertEqual(x.prevKey(0.5), 0.0)
        self.assertEqual(x.prevKey(1.0), 0.0)
        self.assertEqual(x.prevKey(1.5), 1.0)
        self.assertEqual(x.prevKey(2.0), 1.0)
        self.assertEqual(x.prevKey(2.5), 2.0)

    def test_valueIteration(self):
        x = NativeCore.MapWithIndex()
        x[0.0] = 0.0
        x[1.0] = 1.0
        x[2.0] = 2.0

        self.assertEqual(x.nextValue(-0.5), 0.0)
        self.assertEqual(x.nextValue(0.0), 1.0)
        self.assertEqual(x.nextValue(0.5), 1.0)
        self.assertEqual(x.nextValue(1.0), 2.0)
        self.assertEqual(x.nextValue(1.5), 2.0)
        self.assertEqual(x.nextValue(2.0), None)
        self.assertEqual(x.nextValue(2.5), None)

        self.assertEqual(x.prevValue(-0.5), None)
        self.assertEqual(x.prevValue(0.0), None)
        self.assertEqual(x.prevValue(0.5), 0.0)
        self.assertEqual(x.prevValue(1.0), 0.0)
        self.assertEqual(x.prevValue(1.5), 1.0)
        self.assertEqual(x.prevValue(2.0), 1.0)
        self.assertEqual(x.prevValue(2.5), 2.0)

