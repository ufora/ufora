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
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.native.Json as NativeJson


_testKeyspace = SharedState.Keyspace("TakeHighestIdKeyType",
    NativeJson.Json("TestSpace"),
    1
    )

class ListenerTest(unittest.TestCase):
    def setUp(self):
        self.harness = SharedStateTestHarness.SharedStateTestHarness(True)

    def test_basic_listener(self):
        v1 = self.harness.newView()
        v2 = self.harness.newView()

        while not v1.waitConnectTimeout(.1):
            pass

        while not v2.waitConnectTimeout(.1):
            pass

        l = SharedState.Listener(v1)
        v1.subscribe(SharedState.KeyRange(_testKeyspace, 0, None, None, True, True), True)
        v2.subscribe(SharedState.KeyRange(_testKeyspace, 0, None, None, True, True), True)

        self.assertIsInstance(l.get()[0][1], SharedState.SharedStateNative.KeyRange)

        self.assertTrue(len(l.get(.1)) == 0)

        self.assertTrue(len(l.getNonblock()) == 0)



        testKey = SharedState.Key(_testKeyspace, (NativeJson.Json('test'),))
        with SharedState.Transaction(v2):
            v2[testKey] = NativeJson.Json('test2')

        v2.flush()
        v1.flush()

        updates = l.get(1)
        self.assertTrue(len(updates) == 1)
        self.assertEqual(updates[0][0], "KeyUpdates")
        self.assertIsInstance(updates[0][1], list)
        self.assertTrue(updates[0][1][0] == testKey)

        with SharedState.Transaction(v2):
            v2[testKey] = NativeJson.Json('newer test')

        v2.flush()
        v1.flush()

        updates = l.get(1)
        self.assertTrue(len(updates) == 1)
        self.assertEqual(updates[0][0], "KeyUpdates")
        self.assertIsInstance(updates[0][1], list)
        self.assertTrue(updates[0][1][0] == testKey)

