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
import time

import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.core.JsonPickle as JsonPickle
import ufora.BackendGateway.ComputedGraph.ComputedGraphTestHarness as ComputedGraphTestHarness

import ufora.distributed.SharedState.ComputedGraph as CGSS
import ufora.distributed.SharedState.ComputedGraph.Node as Node
import ufora.distributed.SharedState.ComputedGraph.Property as Property
import ufora.distributed.SharedState.ComputedGraph.SharedStateSynchronizer \
                                                            as SharedStateSynchronizer
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.native.Json as NativeJson

from ufora.distributed.SharedState.tests.SharedStateTestHarness import SharedStateTestHarness

class TestComputedGraphSharedState(unittest.TestCase):
    def setUp(self):
        self.sharedState = SharedStateTestHarness(inMemory = True)

        self.keyspacePath = (0, 1)
        self.keyspaceName = Node.keyspacePathToKeyspaceName(self.keyspacePath)
        self.keyName = 'key'
        self.keyValue = 'value'

        self.keyspace = SharedState.Keyspace("TakeHighestIdKeyType", self.keyspaceName, 1)
        self.keyRange = SharedState.KeyRange(self.keyspace, 0, None, None, True, False)

    def test_keyUpload(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.keyUploadTest)

    def test_keyDownload(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.keyDownloadTest)

    def test_propertyWrite(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.propertyWriteTest)

    def test_propertyRead(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.propertyReadTest)

    def test_synchronizerWithNoConnection(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(
            self.synchronizerNoConnection
            )

    def test_synchronizerCallUpdate(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(
            self.synchronizerCallUpdateTest
            )

    def test_synchronizerUpdate(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(
            self.synchronizerUpdateTest
            )

    def keyUploadTest(self, computedGraphTestHarness):
        with self.createSynchronizer():
            self.populateKey()

            def assertValueIsInSharedState(self, key, view):
                self.assertValueUpdatedInSharedState(key, view, self.keyValue)

            self.runInTransaction(self.keyName, assertValueIsInSharedState)


    def keyDownloadTest(self, computedGraphTestHarness):
        def updateValueInSharedState(self, key, view):
            view[key] = JsonPickle.toJson(self.keyValue)

        synchronizer = self.createSynchronizer()
        with synchronizer:
            self.runInTransaction(self.keyName, updateValueInSharedState, False)

            computedGraphKeyspace, computedGraphKey = self.createKey()

            self.synchronizerWaitForKey(self.keyName, synchronizer)

            self.assertEqual(computedGraphKey.value, (self.keyValue,))

    def propertyWriteTest(self, computedGraphTestHarness):
        synchronizer = self.createSynchronizer()
        with synchronizer:
            location = TestLocation(keyspace = self.keyspacePath)

            location.sharedStateSubspace.keyspace.waitLoaded()

            location.testProperty = self.keyValue
            synchronizer.update()

            def assertValueIsInSharedState(self, key, view):
                self.assertValueUpdatedInSharedState(key, view, self.keyValue)

            self.runInTransaction(
                'testProperty',
                assertValueIsInSharedState
                )


    def propertyReadTest(self, computedGraphTestHarness):
        synchronizer = self.createSynchronizer()
        with synchronizer:
            location = TestLocation(keyspace = self.keyspacePath)

            def updateValueInSharedState(self, key, view):
                view[key] = JsonPickle.toJson(self.keyValue)

            self.runInTransaction(
                'testProperty',
                updateValueInSharedState,
                False
                )

            self.synchronizerWaitForKey("testProperty", synchronizer)

            self.assertEqual(location.testProperty, self.keyValue)

    def synchronizerNoConnection(self, computedGraphTestHarness):
        synchronizer = SharedStateSynchronizer.SharedStateSynchronizer()
        synchronizer.update()
        # This test just verifies that the call to update() doesn't blow up
        # when the synchronizer doesn't have a shared state view

    def synchronizerCallUpdateTest(self, computedGraphTestHarness):
        synchronizer = self.createSynchronizer()
        synchronizer.update()
        # This test just verifies that the call to update() doesn't blow up

    def synchronizerUpdateTest(self, computedGraphTestHarness):
        synchronizer = self.createSynchronizer()

        def updateValueInSharedState(self, key, view):
            view[key] = JsonPickle.toJson(self.keyValue)

        self.runInTransaction(self.keyName, updateValueInSharedState, False)

        with synchronizer:
            assert SharedStateSynchronizer.getView() is not None

            computedGraphKeyspace, computedGraphKey = self.createKey()

            self.synchronizerWaitForKey(self.keyName, synchronizer)

            self.assertEqual(computedGraphKey.value, (self.keyValue,))


    def runInTransaction(self, keyPathElement, toRun, waitForKeyToLoad = True):
        """
        Runs a specified function in a shared state transaction.

        toRun is a function that takes the following argumenst:
            self - a self reference
            key  - the shared state key used by the test
            view - the a shared state view subscribed to the key range
                   that contains key.
            waitForKeyToLoad - wait for SharedState to actually load the
                    key
        """
        view = self.sharedState.newView()
        view.subscribe(self.keyRange)

        passes = 0
        while passes < 100:
            with SharedState.Transaction(view):
                key = SharedState.Key(self.keyspace, (Node.keyPathToKeyName((keyPathElement,)),))

                if not waitForKeyToLoad or view[key] is not None:
                    toRun(self, key, view)
                    return

            passes += 1
            time.sleep(.1)

        assert False, "Test timed out"


    def assertValueUpdatedInSharedState(self, key, view, expectedValue):
        self.assertIsNotNone(view[key])
        value = view[key].value()
        self.assertEqual(JsonPickle.fromJson(value), self.keyValue)


    def populateKey(self):
        keyspace, key = self.createKey()

        keyspace.waitLoaded()

        key.value = (self.keyValue,)

        SharedStateSynchronizer.getSynchronizer().update()
        SharedStateSynchronizer.getSynchronizer().commitPendingWrites()

        return key

    def createKey(self):
        keyspace = CGSS.Node.Keyspace(keyspacePath = self.keyspacePath)
        return (keyspace, keyspace.subspace.subspace(self.keyName))

    def createSynchronizer(self):
        synchronizer = SharedStateSynchronizer.SharedStateSynchronizer()
        synchronizer.attachView(self.sharedState.newView())

        return synchronizer

    def synchronizerWaitForKey(self, keyName, synchronizer):
        isSet = [False]
        updateDict = {}

        keyName = Node.keyPathToKeyName((keyName,))

        class Listener:
            def keysLoaded(listenerSelf, keyValueDict, isInitialLoad):
                if keyName in keyValueDict:
                    isSet[0] = True

                updateDict.update(keyValueDict)

        synchronizer.addKeyspaceListener(self.keyspaceName, Listener(), NativeJson.Json(()))

        passes = 0
        while not isSet[0] and passes < 100:
            time.sleep(.1)
            synchronizer.update()

            passes += 1

        if not isSet[0]:
            assert False, "Failed to load %s. did see %s" % (keyName, updateDict)





class TestLocation(ComputedGraph.Location):
    keyspace=object

    def sharedStateSubspace(self):
        return CGSS.Node.Keyspace(keyspacePath=self.keyspace).subspace

    testProperty = Property.Property()

