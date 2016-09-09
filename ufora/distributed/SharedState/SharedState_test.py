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

import logging
import os
import time
import uuid
import resource
import tempfile
import shutil
import threading
import ufora.native.Json as NativeJson
import traceback
import unittest
import ufora.config.Setup as Setup
import ufora.native.Json as JsonNative
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness

DEFAULT_PASS_COUNT = 5
DEFAULT_THREAD_COUNT = 10


class TestSharedState(unittest.TestCase):
    def clientThread(self, harness, passIndex, threadIndex, totalThreadCount,
                        successList, failureList, connectedThreads, connectedThreadEvent,
                        viewList,
                        blockUntilConnected
                        ):
        try:
            logging.info("Connecting to SharedState in thread %s", threadIndex)
            try:
                view = harness.newView()
                viewList.append(view)
            finally:
                connectedThreads.append(threadIndex)

                if len(connectedThreads) == totalThreadCount:
                    connectedThreadEvent.set()
                    logging.debug("All reconnection test threads have connected.")


            if blockUntilConnected:
                connectedThreadEvent.wait()

            logging.info("Have view in thread %s", threadIndex)

            logging.info("Connected to shared state in thread %s", threadIndex)

            harness.subscribeToKeyspace(view, NativeJson.Json("data"))

            harness.writeToKeyspace(
                view,
                NativeJson.Json("data"),
                NativeJson.Json(str(threadIndex)),
                NativeJson.Json(str(passIndex))
                )

            t0 = time.time()

            while True:
                itemDict = dict(harness.getAllItemsFromView(view, NativeJson.Json("data")))

                allAreCurPass = True
                if len(itemDict) == totalThreadCount:
                    for i in itemDict:
                        if itemDict[i] != NativeJson.Json(str(passIndex)):
                            allAreCurPass = False

                if allAreCurPass:
                    successList.append(threadIndex)
                    return

                time.sleep(.01)
                if time.time() - t0 > 5.0:
                    failureList.append("Bad dict: %s" % itemDict)
                    return

            view.flush()
        except:
            failureList.append("Exception: " + traceback.format_exc())

    def rapidReconnectionTest(self, harness, totalThreadCount, passCount, blockUntilConnected):
        for passIndex in range(passCount):
            successes = []
            failures = []

            logging.info("Starting connect-pass %s", passIndex)

            threads = []
            connectedThreads =  []
            viewList = []
            allConnectedEvent = threading.Event()

            for threadIndex in range(totalThreadCount):
                threads.append(
                    threading.Thread(
                        target=self.clientThread,
                        args=(harness, passIndex, threadIndex,
                                    totalThreadCount, successes, failures, connectedThreads,
                                    allConnectedEvent,
                                    viewList,
                                    blockUntilConnected
                                    )
                        )
                    )
                threads[-1].start()

            for t in threads:
                t.join()

            logging.debug("All reconnection test threads joined.")

            viewList = []

            logging.debug("All views destroyed.")

            for f in failures:
                logging.warn("Failure: %s", f)

            assert len(successes) == totalThreadCount, \
                "Failed on pass %s. %s instead of %s. %s marked failures" % \
                    (passIndex, len(successes), totalThreadCount, len(failures))

            successes = []
            failures = []

            time.sleep(.25)
            logging.info("DONE SLEEPING\n\n\n\n\n")

    def getHarness(self, **kwds):
        return SharedStateTestHarness.SharedStateTestHarness(**kwds)

    def test_rapid_connections_InMemory_BlockUntilConnected(self):
        harness = self.getHarness(inMemory=True, port=Setup.config().sharedStatePort)

        try:
            self.rapidReconnectionTest(
                harness,
                totalThreadCount=DEFAULT_THREAD_COUNT,
                passCount=DEFAULT_PASS_COUNT,
                blockUntilConnected=True
                )
        finally:
            time.sleep(0.01)
            harness.teardown()

    def test_rapid_connections_UsingSockets_BlockUntilConnected(self):
        harness = self.getHarness(inMemory=False, port=Setup.config().sharedStatePort)

        try:
            self.rapidReconnectionTest(
                harness,
                totalThreadCount=DEFAULT_THREAD_COUNT,
                passCount=DEFAULT_PASS_COUNT,
                blockUntilConnected=True
                )
        finally:
            harness.teardown()

    def test_rapid_connections_InMemory(self):
        harness = self.getHarness(inMemory=True, port=Setup.config().sharedStatePort)

        try:
            self.rapidReconnectionTest(
                harness,
                totalThreadCount=DEFAULT_THREAD_COUNT,
                passCount=DEFAULT_PASS_COUNT,
                blockUntilConnected=False
                )
        finally:
            time.sleep(0.01)
            harness.teardown()

    def test_rapid_connections_UsingSockets(self):
        harness = self.getHarness(inMemory=False, port=Setup.config().sharedStatePort)

        try:
            self.rapidReconnectionTest(
                harness,
                totalThreadCount=DEFAULT_THREAD_COUNT,
                passCount=DEFAULT_PASS_COUNT,
                blockUntilConnected=False
                )
        finally:
            harness.teardown()

    def test_listener(self):
        harness = self.getHarness(inMemory=True)
        try:
            v1 = harness.newView()
            v2 = harness.newView()

            l = SharedState.Listener(v2)

            space = SharedState.Keyspace("ComparisonKeyType", NativeJson.Json("TestSpace"), 1)
            rng = SharedState.KeyRange(space, 0, None, None, True, False)

            v1.subscribe(rng)
            v2.subscribe(rng)

            keysToWrite = [JsonNative.Json(str(x)) for x in range(40)]

            def writer():
                with SharedState.Transaction(v1):
                    for keyName in keysToWrite:
                        key = SharedState.Key(space, (keyName,))
                        v1[key] = JsonNative.Json("value")

            changedKeys = []
            def reader():
                while len(changedKeys) < len(keysToWrite):
                    updates = l.get()
                    for updateType, update in updates:
                        if updateType == "KeyUpdates":
                            for key in update:
                                changedKeys.append(key[0])

            writerThread = threading.Thread(target=writer)
            readerThread = threading.Thread(target=reader)

            writerThread.start()
            readerThread.start()

            writerThread.join()
            readerThread.join()

            self.assertEqual(set(keysToWrite), set(changedKeys))

        finally:
            time.sleep(0.01)
            harness.teardown()

    def test_flush(self):
        harness = self.getHarness(inMemory=True)

        try:
            v1 = harness.newView()

            space = SharedState.Keyspace("ComparisonKeyType", NativeJson.Json("TestSpace"), 1)
            rng = SharedState.KeyRange(space, 0, None, None, True, False)

            v1.subscribe(rng)

            keysToWrite = [str(x) for x in range(40)]

            value = "value" * 100 * 1024

            with SharedState.Transaction(v1):
                self.assertRaises(UserWarning, v1.flush, True)

            with SharedState.Transaction(v1):
                for keyName in keysToWrite:
                    key = SharedState.Key(space, (NativeJson.Json(keyName),))
                    v1[key] = NativeJson.Json(value)

            v1.flush()
        finally:
            time.sleep(0.01)
            harness.teardown()

    def test_file_management(self):
        tempDir = tempfile.mkdtemp()

        curOpenFiles = len(os.listdir('/proc/%s/fd' % os.getpid()))

        OPEN_FILE_LIMIT = 200

        if curOpenFiles >= OPEN_FILE_LIMIT:
            os.system("ls -alh /proc/%s/fd" % os.getpid())

        self.assertTrue(curOpenFiles < OPEN_FILE_LIMIT, "Too many open files: %s" % curOpenFiles)

        soft, hard = resource.getrlimit(resource.RLIMIT_OFILE)

        harness = self.getHarness(inMemory=True,
                                  cachePathOverride=tempDir,
                                  maxOpenFiles=15)
        try:
            v1 = harness.newView()
            resource.setrlimit(resource.RLIMIT_OFILE, (curOpenFiles + 30, hard))

            for ix in range(128):
                space = SharedState.Keyspace("TakeHighestIdKeyType",
                                             NativeJson.Json("TestSpace%s" % ix),
                                             1)
                rng = SharedState.KeyRange(space, 0, None, None, True, False)
                v1.subscribe(rng)
                key = SharedState.Key(space, (NativeJson.Json('key%s' % ix),))
                with SharedState.Transaction(v1):
                    v1[key] = NativeJson.Json('value %s' % ix)
        finally:
            time.sleep(0.01)
            harness.teardown()
            resource.setrlimit(resource.RLIMIT_OFILE, (soft, hard))
            try:
                shutil.rmtree(tempDir)
            except:
                pass

    def test_require_subscription_manager(self):
        tempDir = tempfile.mkdtemp()
        try:
            testKeyspace = SharedState.Keyspace("TakeHighestIdKeyType",
                                                NativeJson.Json("TestSpace"),
                                                1)
            harness = self.getHarness(inMemory=True, cachePathOverride=tempDir)


            v1 = harness.newView()
            v1.subscribe(SharedState.KeyRange(testKeyspace, 0, None, None, True, False))

            for ix in range(1000):
                with SharedState.Transaction(v1):
                    key = SharedState.Key(testKeyspace, (NativeJson.Json("key"),))
                    v1[key] = NativeJson.Json(str(ix))
            time.sleep(2)

            v2 = harness.newView()
            v2.setMustSubscribe(False)
            with SharedState.Transaction(v2):
                key = SharedState.Key(testKeyspace, (NativeJson.Json("key"),))
                value = 'value is' + uuid.uuid4().hex
                v2[key] = NativeJson.Json(value)
            time.sleep(2)
            def toTry():
                with SharedState.Transaction(v2):
                    key = SharedState.Key(testKeyspace, (NativeJson.Json("key"),))
                    value = 'value is' + uuid.uuid4().hex
                    v2[key] = NativeJson.Json(value)

            self.assertRaises(UserWarning, toTry)
        finally:
            time.sleep(0.01)
            harness.teardown()
            shutil.rmtree(tempDir)

    def test_require_subscription_view(self):
        try:
            testKeyspace = SharedState.Keyspace("TakeHighestIdKeyType",
                                                NativeJson.Json("TestSpace"),
                                                1)
            harness = self.getHarness(inMemory=True)
            v1 = harness.newView()
            def toTry():
                with SharedState.Transaction(v1):
                    key = SharedState.Key(testKeyspace, ("key",))
                    v1[key] = NativeJson.Json('this is a test value')

            self.assertRaises(UserWarning, toTry)
        finally:
            time.sleep(0.01)
            harness.teardown()

    def test_persistence(self):
        tempDir = tempfile.mkdtemp()

        try:
            testValues = {}
            def testWrite(passIx):
                try:
                    testKeyspaces = [
                        SharedState.Keyspace("TakeHighestIdKeyType",
                                             NativeJson.Json("TestSpace%s" % ix), 3) \
                        for ix in range(3)
                        ]

                    harness = self.getHarness(inMemory=True, cachePathOverride=tempDir)
                    v1 = harness.newView()
                    for space in testKeyspaces:
                        rng = SharedState.KeyRange(space, 0, None, None, True, False)
                        v1.subscribe(rng)

                    for ix in range(9):
                        keyspaceIx = (ix+passIx) % len(testKeyspaces)

                        space = testKeyspaces[keyspaceIx] #random.choice(testKeyspaces)
                        with SharedState.Transaction(v1):
                            key = SharedState.Key(space,
                                                  (NativeJson.Json("key %s" % ix), NativeJson.Json(''), NativeJson.Json('')))
                            value = JsonNative.Json(
                                '<value is %s in space %s on pass %s: %s>' %
                                    (ix, keyspaceIx, passIx, uuid.uuid4().hex)
                                )
                            v1[key] = value
                            testValues[key] = value

                    v1.flush()

                    time.sleep(0.01)
                    harness.teardown()
                    harness = self.getHarness(inMemory=True, cachePathOverride=tempDir)

                    v1 = harness.newView()
                    for space in testKeyspaces:
                        rng = SharedState.KeyRange(space, 0, None, None, True, False)
                        v1.subscribe(rng)

                    for key, value in testValues.iteritems():
                        self.assertSharedStateKeyResolvesToValue(key, v1, testValues[key])
                except:
                    logging.warn("Exception: %s", traceback.format_exc())
                    raise
                finally:
                    time.sleep(0.01)
                    harness.teardown()

            for ix in range(2):
                testWrite(ix)
        finally:
            shutil.rmtree(tempDir)

    def assertSharedStateKeyResolvesToValue(self, key, view, value):
        passes = 0
        lastVal = None
        while passes < 100:
            with SharedState.Transaction(view):
                if view[key] is not None:
                    lastVal = view[key].value()
                    self.assertEqual(value, lastVal)
                    return

                passes += 1
                time.sleep(.1)

        assert False, "key %s never resolved to value %s. stayed as %s" % (key, value, lastVal)

