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
import random
import ufora.native.Storage as Storage


class TestLogSerialization(unittest.TestCase):
    def setUp(self):
        self.curPathNumber = 0

    def genLines(self):
        return tuple([''.join(chr(random.randint(ord('A'), ord('z')))
            for y in range(128))
                for x in range(20)])

    def test_serialization(self):
        lines = self.genLines()
        pathA, pathB = 'pathA', 'pathB'
        serializers = Storage.OpenJsonSerializers()
        serializedA, serializedB = [], []

        for line in lines:
            serializedA.append(serializers.serialize(pathA, line))
            serializedB.append(serializers.serialize(pathB, line))


        success, contents = Storage.deserializeAsVector(serializedA)
        self.assertTrue(success)
        self.assertEqual(tuple(contents), lines)

        success, contents = Storage.deserializeAsVector(serializedB)
        self.assertTrue(success)
        self.assertEqual(tuple(contents), lines)

    def test_type_serialization(self):
        lines = self.genLines()
        pathA, pathB = 'pathA', 'pathB'
        serializers = Storage.OpenJsonSerializers()
        serializedA, serializedB = [], []

        serializedA = serializers.serializeAsVector(pathA, list(lines))
        serializedB = serializers.serializeAsVector(pathB, list(lines))

        success, contents = Storage.deserializeAsType(serializedA)
        self.assertTrue(success)
        self.assertEqual(tuple(contents), lines)

        success, contents = Storage.deserializeAsType(serializedB)
        self.assertTrue(success)
        self.assertEqual(tuple(contents), lines)

