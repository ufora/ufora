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

"""
Unit tests for PersistentCacheIndex
"""

import time
import unittest
import threading

import ufora.distributed.SharedState.ComputedGraph.SharedStateSynchronizer \
                                                            as SharedStateSynchronizer
from ufora.distributed.SharedState.tests.SharedStateTestHarness import SharedStateTestHarness
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedGraph.ComputedGraphTestHarness as ComputedGraphTestHarness

import ufora.native.Cumulus as CumulusNative
import ufora.native.Hash as HashNative
import ufora.native.TCMalloc as TCMallocNative

HashSet = HashNative.ImmutableTreeSetOfHash


sha1 = HashNative.Hash.sha1

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

class TestPersistentCacheIndex(unittest.TestCase):
    def setUp(self):
        self.sharedState = SharedStateTestHarness(inMemory=True)
        self.synchronizer = SharedStateSynchronizer.SharedStateSynchronizer()
        self.synchronizer.attachView(self.sharedState.newView())
        self.synchronizer.__enter__()

    def tearDown(self):
        self.synchronizer.__exit__(None, None, None)

    def waitForSync(self, predicate, *synchronizers):
        if not synchronizers:
            synchronizers = [self.synchronizer]

        ComputedGraph.assertHasGraph()
        passes = 0
        while passes < 100:
            for s in synchronizers:
                s.update()
            if predicate():
                break
            time.sleep(.1)
            passes += 1
        self.assertTrue(predicate())

    @ComputedGraphTestHarness.UnderHarness
    def test_persistentCacheUnderLoad(self):
        cppView1 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )

        t0 = time.time()
        #add 100k pages, which is enough for about 5 TB of data
        for index in range(100000):
            if index % 1000 == 0 and index > 0:
                print index, (time.time() - t0) / (index / 1000.0), " seconds per 1000"
            cppView1.addPage(sha1("page" + str(index)), HashSet(), 1, sha1(""))

        print "took ", time.time() - t0, " to add 100k."

        t1 = time.time()

        bytes0 = TCMallocNative.getBytesUsed()

        cppView2 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )

        while cppView2.totalBytesInCache() < 100000:
            time.sleep(.1)
            print cppView2.totalBytesInCache()

        print "took ", time.time() - t1, " to load 100k. Total RAM is ", (TCMallocNative.getBytesUsed() - bytes0) / 1024 / 1024.0, " MB per view"\

    @ComputedGraphTestHarness.UnderHarness
    def test_circularPageReferencesAreInvalid(self):
        self.circularPageReferenceTest(True)

    @ComputedGraphTestHarness.UnderHarness
    def test_noncircularPageReferencesAreValid(self):
        self.circularPageReferenceTest(False)

    def circularPageReferenceTest(self, shouldBeInvalid):
        cppView1 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )
        computationId = CumulusNative.ComputationId.Root(
            sha1("computation")
            )

        checkpointRequest = CumulusNative.CheckpointRequest(0.0, True, computationId)

        cppView1.addBigvec(sha1("bigvec1"), HashSet() + sha1("page1"), 2, sha1(""))
        cppView1.addPage(sha1("page1"), (HashSet() + sha1("bigvec1")) if shouldBeInvalid else HashSet(), 1, sha1(""))
        cppView1.addCheckpointFile(checkpointRequest, sha1("file"), HashSet() + sha1("bigvec1"), 2, sha1(""))
        cppView1.addCheckpoint(checkpointRequest, HashSet() + sha1("file"), 2, sha1(""), True, 1.0, HashSet())

        self.assertTrue(
            len(cppView1.computeInvalidObjects()) ==
                (4 if shouldBeInvalid else 0),
            "%s != %s" % (len(cppView1.computeInvalidObjects()), (4 if shouldBeInvalid else 0))
            )

    @ComputedGraphTestHarness.UnderHarness
    def test_orphanedPageIsCollected(self):
        cppView1 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )
        cppView1.addPage(sha1("page1"), HashSet(), 1, sha1(""))
        self.assertTrue(len(cppView1.computeInvalidObjects()) == 1)




    @ComputedGraphTestHarness.UnderHarness
    def test_basicPersistentCache(self):
        cppView1 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )

        cppView2 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )

        cppView1.addPage(sha1("page1"), HashSet(), 1, sha1(""))
        cppView1.addBigvec(sha1("bigvec1"), HashSet() + sha1("page1"), 2, sha1(""))
        cppView1.addPage(sha1("page2"), HashSet() + sha1("bigvec1"), 3, sha1(""))
        cppView1.addBigvec(sha1("bigvec2"), HashSet() + sha1("page2"), 4, sha1(""))

        self.assertEqual(cppView1.totalBytesInCache(), 10)

        def seesEverything():
            if not cppView2.pageExists(sha1("page1")):
                return False
            if not cppView2.pageExists(sha1("page2")):
                return False
            if not cppView2.bigvecExists(sha1("bigvec1")):
                return False
            if not cppView2.bigvecExists(sha1("bigvec2")):
                return False

            return True

        self.waitForSync(seesEverything)

        for view in [cppView1, cppView2]:
            self.assertEqual(view.pageBytecount(sha1("page1")), 1)
            self.assertEqual(view.bigvecBytecount(sha1("bigvec1")), 2)
            self.assertEqual(view.pageBytecount(sha1("page2")), 3)
            self.assertEqual(view.bigvecBytecount(sha1("bigvec2")), 4)
            self.assertEqual(view.totalBytesInCache(), 10)


    @ComputedGraphTestHarness.UnderHarness
    def test_writing_while_disconnected(self):
        currentView = [self.sharedState.newView()]

        cppView1 = CumulusNative.PersistentCacheIndex(
            currentView[0],
            callbackScheduler
            )

        def writeInLoop():
            for ix in range(100):
                time.sleep(0.01)
                cppView1.addPage(sha1("page" + str(ix)),HashSet(), ix, sha1(""))

        thread1 = threading.Thread(target=writeInLoop)
        thread1.start()

        def disconnectAndReconnectInLoop():
            ix = 0
            while thread1.isAlive():
                ix += 1
                time.sleep(0.004)
                currentView[0].disconnect()
                currentView[0] = self.sharedState.newView()
                cppView1.resetView(currentView[0])

        thread2 = threading.Thread(target=disconnectAndReconnectInLoop)
        thread2.start()

        thread1.join()
        thread2.join()

        self.assertTrue(cppView1.timesViewReconnected() > 10)

        cppView2 = CumulusNative.PersistentCacheIndex(
            self.sharedState.newView(),
            callbackScheduler
            )

        time.sleep(2.0)

        count1 = 0
        count2 = 0
        for ix in range(100):
            if cppView1.pageExists(sha1("page" + str(ix))):
                count1 += 1

            if cppView2.pageExists(sha1("page" + str(ix))):
                count2 += 1

        self.assertTrue(count1 == 100 and count2 == 100, (count1, count2))

