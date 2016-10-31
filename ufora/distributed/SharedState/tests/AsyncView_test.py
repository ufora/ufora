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
import threading
import Queue
import random
import ufora.native.Json as NativeJson
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.distributed.SharedState.AsyncView as AsyncView
import ufora.distributed.SharedState.SharedState as SharedState

class TestAsyncView(unittest.TestCase):
    def setUp(self):
        self.testKeyspace = SharedState.Keyspace("TakeHighestIdKeyType",
                                                 NativeJson.Json("TestSpace"),
                                                 1)
        self.harness = SharedStateTestHarness.SharedStateTestHarness(inMemory=True)

    def tearDown(self):
        self.harness.teardown()

    def subscribeToTestKeyspace(self, view, block=True):
        view.subscribe(
            SharedState.KeyRange(self.testKeyspace, 0, None, None, True, False),
            block
            )

    def test_async_view(self):
        try:
            simpleView = None
            toWrite = {
                NativeJson.Json(str(ix)): NativeJson.Json('value-%s' % ix)
                for ix in range(100)
                }
            written = {}

            v1 = self.harness.newView()

            self.subscribeToTestKeyspace(v1)

            for key, value in toWrite.iteritems():
                with SharedState.Transaction(v1):
                    key = SharedState.Key(self.testKeyspace, (key,))
                    v1[key] = value
                    written[key[0]] = value

            v1.flush()


            received = {}

            newKeysWritten = threading.Condition()
            def onConnected(_):
                def callback(keysDict):
                    for key, value in keysDict.iteritems():
                        received[key[0]] = value

                    with newKeysWritten:
                        newKeysWritten.notify()

                simpleView.subscribeToKeyspace(self.testKeyspace, 0, callback)

            simpleView = AsyncView.AsyncView(self.harness.viewFactory,
                                             onConnectCallback=onConnected)

            simpleView.startService()

            while set(received.values()) != set(written.values()):
                with newKeysWritten:
                    newKeysWritten.wait()

            self.assertEqual(set(received.values()), set(written.values()))

        finally:
            if simpleView:
                simpleView.stopService()
            self.harness.teardown()


    def test_two_keyspaces(self):
        try:
            toWrite = Queue.Queue()
            space1 = SharedState.Keyspace("TakeHighestIdKeyType", NativeJson.Json("TestSpace1"), 1)
            space2 = SharedState.Keyspace("TakeHighestIdKeyType", NativeJson.Json("TestSpace2"), 1)


            def callback1(items):
                for key in items.iterkeys():
                    self.assertEqual(key.keyspace, NativeJson.Json("TestSpace1"))
                    toWrite.task_done()

            def callback2(items):
                for key in items.iterkeys():
                    self.assertEqual(key.keyspace, NativeJson.Json("TestSpace2"))
                    toWrite.task_done()


            def onConnected(_):
                simpleView.subscribeToKeyspace(space1, 0, callback1)
                simpleView.subscribeToKeyspace(space2, 0, callback2)

            simpleView = AsyncView.AsyncView(self.harness.viewFactory,
                                             onConnected)

            simpleView.startService()

            v1 = self.harness.newView()

            v1.subscribe(SharedState.KeyRange(space1, 0, None, None, True, False),
                         True)

            v1.subscribe(SharedState.KeyRange(space2, 0, None, None, True, False),
                         True)


            for x in range(100):
                space = space1
                if random.random() < .5:
                    space = space2
                toWrite.put((str(x), space))
                with SharedState.Transaction(v1):
                    v1[SharedState.Key(space, (NativeJson.Json(str(x)),))] = space.name

            toWrite.join()


        finally:
            if simpleView:
                simpleView.stopService()
            self.harness.teardown()

    def test_add_transaction(self):
        try:
            toWrite = {
                NativeJson.Json(str(x)): NativeJson.Json('value-%s' % x)
                for x in range(50)
                }
            simpleView = None

            def onConnect(_):
                def callback(value):
                    for key, value in toWrite.iteritems():
                        key = SharedState.Key(self.testKeyspace, (key,))
                        simpleView.pushTransaction(key, value)

                deferred = simpleView.subscribeToKeyspace(self.testKeyspace, 0, callback)
                deferred.addCallbacks(callback, lambda value: None)

            simpleView = AsyncView.AsyncView(self.harness.viewFactory,
                                             onConnectCallback=onConnect)

            simpleView.startService()

            v1 = self.harness.newView()
            listener = SharedState.Listener(v1)

            self.subscribeToTestKeyspace(v1)

            toCheck = dict(toWrite)
            while len(toCheck):
                updates = listener.get()
                for updateType, update in updates:
                    if updateType == "KeyUpdates":
                        for key in update:
                            if key[0] in toCheck:
                                with SharedState.Transaction(v1):
                                    self.assertEqual(toCheck[key[0]], v1[key].value())
                                del toCheck[key[0]]

        finally:
            if simpleView:
                simpleView.stopService()
            self.harness.teardown()

    def test_keyspace_iteration(self):
        try:
            toWrite = {
                NativeJson.Json(str(x)): NativeJson.Json('value-%s' % x)
                for x in range(50)
                }
            simpleView = None

            v1 = self.harness.newView()
            self.subscribeToTestKeyspace(v1)

            for key, value in toWrite.iteritems():
                key = SharedState.Key(self.testKeyspace, (key,))
                with SharedState.Transaction(v1):
                    v1[key] = value

            v1.flush()

            def onConnect(_):
                def checkIteration(value):
                    for key, value in simpleView.keyspaceItems(self.testKeyspace):
                        assert key[0] in toWrite
                        self.assertEqual(toWrite[key[0]], value)

                deferred = simpleView.subscribeToKeyspace(self.testKeyspace,
                                                          0,
                                                          lambda keys: None)
                deferred.addCallbacks(checkIteration, lambda value: None)


            simpleView = AsyncView.AsyncView(self.harness.viewFactory,
                                             onConnectCallback=onConnect)

            simpleView.startService()



        finally:
            if simpleView:
                simpleView.stopService()
            self.harness.teardown()

    def test_events_in_subscription(self):
        asynView = None
        try:
            v1 = self.harness.newView()
            self.subscribeToTestKeyspace(v1)

            for ix in range(100):
                key = SharedState.Key(self.testKeyspace, (NativeJson.Json('test%s' % ix),))
                with SharedState.Transaction(v1):
                    v1[key] = NativeJson.Json('value1')

            done = threading.Event()
            numKeyEvents = [0]
            def onKeyEvents(eventDict):
                numKeyEvents[0] += len(eventDict)


            def onSubscriptionLoaded(_):
                done.set()

            def onConnected(_):
                deferred = asynView.subscribeToKeyspace(self.testKeyspace, 0, onKeyEvents)
                deferred.addCallbacks(onSubscriptionLoaded, lambda error: None)


            asynView = AsyncView.AsyncView(self.harness.viewFactory,
                                           onConnectCallback=onConnected)
            asynView.startService()

            while not done.wait(.1):
                pass

            self.assertEqual(numKeyEvents[0], 100)
        finally:
            asynView.stopService()

