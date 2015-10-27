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
import logging
import random
import ufora.util.ManagedThread as ManagedThread
import uuid

import ufora.config.Setup as Setup
import ufora.native.Json as NativeJson
import ufora.test.ClusterSimulation as ClusterSimulation
import ufora.test.CumulusSimulationUtils as CumulusSimulationUtils

import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory

import ufora.distributed.SharedState.SharedState as SharedState
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

class SharedStateRelayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulator = ClusterSimulation.Simulator.createGlobalSimulator(user='test_admin')
        cls.simulator.startService()
        cls.simulator.verifySharedStateRunning()

        cls.desirePublisher = cls.simulator.desirePublisher

    def stressMultipleSharedStateReadWrites(self, useTcpFactory=False, keysToWrite=20, threadcount=10):
        keyspaceSize = keysToWrite * 5
        subPasses = 10

        if useTcpFactory:
            viewFactory = ViewFactory.ViewFactory.TcpViewFactory(callbackScheduler, address="localhost")
        else:
            viewFactory = self.simulator.getViewFactory()

        worked = {}

        for ix in range(threadcount):
            worked[ix] = False

        def test(threadIx):
            for subPassIx in range(subPasses):
                logging.info("Thread %s starting pass %s", threadIx, subPassIx)
                testKeyspace = SharedState.Keyspace("TakeHighestIdKeyType", NativeJson.Json("TestSpace"), 1)

                view = viewFactory.createView()

                rng = SharedState.KeyRange(testKeyspace, 0, None, None, True, False)
                view.subscribe(rng)

                for ix in range(keysToWrite):
                    with SharedState.Transaction(view):
                        ix = random.randint(0, keyspaceSize)
                        key = SharedState.Key(testKeyspace, (NativeJson.Json("key %s" % ix),))
                        value = uuid.uuid4().hex
                        view[key] = NativeJson.Json(value)

            worked[threadIx] = True

        threads = [ManagedThread.ManagedThread(target=test, args = (ix,)) for ix in range(threadcount)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        expectedDict = {}
        for ix in range(threadcount):
            expectedDict[ix] = True

        self.assertEqual(expectedDict, worked)

    def testWithTcp(self):
        self.stressMultipleSharedStateReadWrites(True, 200)

    def testWithRelay(self):
        self.stressMultipleSharedStateReadWrites(False, 200)

    @classmethod
    def tearDownClass(cls):
        cls.simulator.stopService()

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    import ufora.config.LoginConfiguration as LoginConfiguration
    Mainline.UnitTestMainline(loginConfiguration=LoginConfiguration.LoginConfiguration("test_admin", "asdfasdf", True, {}))

