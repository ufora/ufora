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
import random
import time
import unittest
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.native.Cumulus as CumulusNative
import ufora.native.Hash as HashNative

#import ufora.distributed.Storage.HdfsObjectStore as HdfsObjectStore

callbackScheduler = CallbackScheduler.singletonForTesting()

#note that we are being careful not to use anything from the builtins in these examples
#so that checkpointing is fast. Currently, "FORA.eval" doesn't use the module subsampler,
#so we end up holding the entire builtins if we use it.

def expensiveChildCachecalls(ix):
    return  """
        Vector.range(10).papply(fun(ix) {
            sum(ix, 10**12) + %s
            })
        """ % ix

vecOfVecCalcText = """
    let sum = fun(a,b,f) {
        if (a >= b) return 0
        if (a+1 >= b) return f(a)
        let mid = (a+b)/2;
        return sum(a,mid,f) + sum(mid,b,f)
        }
    let res = [];
    let ix = 0;
    while (ix < 100) {
        res = res + sum(0,100, fun(x) { [[sum(x, 10**6, fun(x){x+1})].paged].paged })
        ix = ix + 1
        }
    res.sum()
    """

vecLoopSumText = """
    let res = 0;
    let ix = 0;
    while (ix < 1000000) {
        res = res + Vector.range(100000).sum()
        ix = ix + 1
        }
    res
    """

repeatedVecInLoop = """
    let v = Vector.range(1000000)
    let ix = 0

    while (ix < 1000000) {
        v = v.apply({_+1}).paged
        ix = ix + 1
        }
    v.sum()
    """

simpleSumInLoopText = """
    let v = Vector.range(1000000).paged;
    let sum = fun(a,b,f) {
        if (a >= b) return 0
        if (a+1 >= b) return f(a)
        let mid = (a+b)/2;
        return sum(a,mid,f) + sum(mid,b,f)
        }

    let res = 0;

    let ix = 0
    while (ix < 100) {
        ix = ix + 1
        res = res + sum(ix, Int64(10**9), {if (_ % 16 == 0) v[(_ * 1024) % size(v)] else _ });
        }

    res
    """

sumInLoopText = """
    let sum = fun(a,b,f) {
        if (a >= b) return 0
        if (a+1 >= b) return f(a)
        let mid = (a+b)/2;
        return sum(a,mid,f) + sum(mid,b,f)
        }

    let res = 0;
    let ix = 0;
    while (ix < 10000) {
        let bound = match(ix%3) with (0) { 1 } (1) { 10 } (2) { 100 };

        res = res + sum(0,bound * 1000000, fun(x) { x + 1 })

        ix = ix + 1
        }
    res
    """

bigSumText = """
    let sum = fun(a,b,f) {
        if (a >= b) return 0
        if (a+1 >= b) return f(a)
        let mid = (a+b)/2;
        return sum(a,mid,f) + sum(mid,b,f)
        }

    sum(0,10**13,{_})
    """

cachedBigSumText = """
    let sum = fun(a,b,f) {
        if (a >= b) return 0
        if (a+1 >= b) return f(a)
        let mid = (a+b)/2;
        return sum(a,mid,f) + sum(mid,b,f)
        }

    cached(sum(0,10**13,{_}))[0]
    """

TIMEOUT = 30

class CheckpointingTest(unittest.TestCase):
    def waitForAllCheckpointsToClear(self, simulation, timeout = TIMEOUT):
        t0 = time.time()
        while time.time() < t0 + timeout:
            if not simulation.getGlobalScheduler().anyOutstandingTriggeredCheckpoints():
                return
            time.sleep(0.01)

        assert False, "timed out"

    def timestampOfMostRecentFullCheckpoint(self, simulation, onlyUnfinished = True):
        if not simulation.getGlobalScheduler():
            return None

        statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(onlyUnfinished, True)
        if len(statuses):
            (computation, (checkpointStatus, checkpointRequest)) = statuses[0]

            timestamp = checkpointRequest.timestamp
            isFull = checkpointRequest.writeToStorage

            if isFull:
                return timestamp

    def timestampOfMostRecentCheckpoint(self, simulation):
        if not simulation.getGlobalScheduler():
            return None

        statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, False)
        if len(statuses):
            (computation, (checkpointStatus, checkpointRequest)) = statuses[0]

            return checkpointRequest.timestamp

    def timeElapsedOfMostRecentCheckpoints(self, simulation, onlyUnfinished = True, onlyCommitted = False):
        if not simulation.getGlobalScheduler():
            return {}

        statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(onlyUnfinished, onlyCommitted)
        return {status[0]: status[1][0].statistics.timeSpentInCompiler for status in statuses}

    def totalTimeElapsedOfMostRecentCheckpoints(self, simulation, onlyUnfinished = True, onlyCommitted = False):
        return sum(self.timeElapsedOfMostRecentCheckpoints(simulation, onlyUnfinished, onlyCommitted).values(), 0)

    def waitForCheckpoint(self, simulation, priorCheckpoint = None, checkInterval = 0.1, onlyUnfinished = True):
        t1 = time.time()
        foundFullCheckpoint = False
        while time.time() - t1 < TIMEOUT and not foundFullCheckpoint:
            scheduler = simulation.getGlobalScheduler()
            if scheduler:
                statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(onlyUnfinished, False)
                if statuses:
                    checkpointSecondsElapsed = statuses[0][1][0].statistics.timeSpentInCompiler

                    if priorCheckpoint is None or priorCheckpoint < checkpointSecondsElapsed:
                        foundFullCheckpoint = True

            if not foundFullCheckpoint:
                time.sleep(checkInterval)

        if foundFullCheckpoint:
            return checkpointSecondsElapsed

    def waitForNFullCheckpoints(self, simulation, count, checkInterval = 0.1):
        t1 = time.time()
        while time.time() - t1 < TIMEOUT:
            scheduler = simulation.getGlobalScheduler()
            found = []
            if scheduler:
                statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, True)
                for (computation, (stats, checkpoint)) in statuses:
                    if checkpoint.writeToStorage:
                        checkpointSecondsElapsed = stats.statistics.timeSpentInCompiler
                        found.append(checkpointSecondsElapsed)

            if len(found) < count:
                time.sleep(checkInterval)
            else:
                return found


    def waitForFullCheckpoint(self, simulation, priorCheckpoint = None, checkInterval = 0.1, onlyUnfinished = True):
        t1 = time.time()
        foundFullCheckpoint = False
        while time.time() - t1 < TIMEOUT and not foundFullCheckpoint:
            scheduler = simulation.getGlobalScheduler()
            if scheduler:
                statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(onlyUnfinished, True)
                if statuses:
                    (computation, (stats, checkpoint)) = statuses[0]
                    if checkpoint.writeToStorage:
                        checkpointSecondsElapsed = stats.statistics.timeSpentInCompiler

                        if priorCheckpoint is None or priorCheckpoint < checkpointSecondsElapsed:
                            foundFullCheckpoint = True

            if not foundFullCheckpoint:
                time.sleep(checkInterval)

        if foundFullCheckpoint:
            return checkpointSecondsElapsed

    def createSimulation(self,
            useHdfsObjectStore=False,
            objectStore=None,
            sharedStateViewFactory=None,
            workerCount=4,
            machineIdHashSeed=None,
            s3Service=None
            ):
        s3 = s3Service or InMemoryS3Interface.InMemoryS3InterfaceFactory()
        return InMemoryCumulusSimulation.InMemoryCumulusSimulation(
            workerCount,
            1,
            memoryPerWorkerMB=100,
            threadsPerWorker=2,
            s3Service=s3,
            objectStore=objectStore,
            sharedStateViewFactory=sharedStateViewFactory,
            machineIdHashSeed=machineIdHashSeed
            )

    def test_checkpointingCumulusClientRequestPathway(self):
        simulation = self.createSimulation()
        #give the simulation a couple of seconds to pick a scheduler
        t0 = time.time()
        while simulation.getGlobalScheduler() is None:
            time.sleep(0.01)
            self.assertTrue(time.time() - t0 < 2.0)

        simulation.getGlobalScheduler().setCheckpointStatusInterval(0.0001)
        count = 0

        try:
            simulation.submitComputation(simpleSumInLoopText)

            while time.time() - t0 < 2.0:
                result = simulation.getCurrentCheckpointStatistics(timeout = TIMEOUT)
                count = count + 1

            self.assertTrue(count > 10)

            print "Total roundtrips: ", count
        finally:
            simulation.teardown()

    def test_checkpointingSystemWritesToS3(self):
        simulation = self.createSimulation()
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            t0 = time.time()
            while simulation.getGlobalScheduler() is None:
                time.sleep(0.01)
                self.assertTrue(time.time() - t0 < TIMEOUT, "never got a scheduler")

            simulation.getGlobalScheduler().setCheckpointStatusInterval(0.01)

            simulation.submitComputation(simpleSumInLoopText)

            time.sleep(1.0)

            count = 0
            lastCheckpoint = None
            while time.time() - t0 < 20.0:
                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

                foundFullCheckpoint = False
                t1 = time.time()
                while time.time() - t1 < 10.0 and not foundFullCheckpoint:
                    statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, True)
                    if len(statuses):
                        (computation, (stats, checkpoint)) = statuses[0]
                        newCheckpoint = checkpoint.timestamp
                        if lastCheckpoint is None or newCheckpoint != lastCheckpoint:
                            lastCheckpoint = newCheckpoint
                            if checkpoint.writeToStorage:
                                foundFullCheckpoint = True
                    time.sleep(.1)

                self.assertTrue(foundFullCheckpoint)
                count += 1
                logging.info(
                    "Total: %d after %s with %d files.",
                    count,
                    time.time() - t0,
                    len(simulation.objectStore.listValues())
                    )

                self.assertGreater(
                    len(simulation.objectStore.listValues()),
                    0)

                guids = simulation.getWorkerVdm(0).getPersistentCacheIndex().allCheckpointedComputationGuids()
                self.assertGreater(
                    len(guids),
                    0,
                    "Didn't write the checkpoint to the persistent cache"
                    )

                for item in simulation.objectStore.listValues():
                    simulation.objectStore.deleteValue(item[0])

        except:
            simulation.dumpSchedulerEventStreams()
            raise
        finally:
            simulation.teardown()

    def test_checkpointingRecoverySimpleSum(self):
        self.recoveryTest(simpleSumInLoopText)

    def test_checkpointingRecoveryVecLoop(self):
        for ix in range(3):
            self.recoveryTest(
                repeatedVecInLoop,
                interval1 = 1.0,
                interval2 = 1.0,
                interval3 = 1.0,
                initialWorkers = 4,
                workersToDrop1 = 3,
                workersToAdd1 = 3,
                machineIdHashSeed=str(ix)
                )

    def test_s3DatasetComputationHashesAreStable(self):
        for ix in range(2):
            s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

            s3().setKeyValue(
                "bucketname",
                "key",
                "this is some data"
                )

            self.recoveryTest("""
                let data = cached(fun() { datasets.s3("bucketname","key") }())[0];

                cached(fun() { sum(0,10**12, fun(ix) { data[ix % size(data)] }) }())[0]
                """,
                s3Service = s3,
                interval1 = 1.0,
                interval2 = 1.0,
                interval3 = 1.0,
                interval4 = 1.0,
                workersToDrop1 = 3,
                workersToAdd1 = 3,
                workersToDrop2 = 3,
                workersToAdd2 = 3,
                machineIdHashSeed=str(ix)
                )

    def test_recoveryWithUnreadDatasetsS3(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        s3().setKeyValue(
            "bucketname",
            "key",
            "this is some data"
            )

        simulation = self.createSimulation(s3Service = s3)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation("""
                let data = datasets.s3("bucketname","key")

                let res = sum(0,10**12)

                data[res % 2]
                """)

            time.sleep(1.0)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
            self.waitForAllCheckpointsToClear(simulation)
        finally:
            simulation.teardown()


    def recoveryTest(self,
                text,
                interval1 = 5.0,
                interval2 = 1.0,
                interval3 = 1.0,
                interval4 = 1.0,
                initialWorkers = 4,
                workersToDrop1 = 1,
                workersToAdd1 = 0,
                workersToDrop2 = 1,
                workersToAdd2 = 0,
                machineIdHashSeed=None,
                s3Service=None
                ):
        simulation = self.createSimulation(machineIdHashSeed=machineIdHashSeed, workerCount = initialWorkers, s3Service = s3Service)

        try:
            self.assertTrue(len(simulation.objectStore.listValues()) == 0)

            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(text)

            time.sleep(interval1)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
            self.waitForAllCheckpointsToClear(simulation)
            checkpointSecondsElapsed = self.totalTimeElapsedOfMostRecentCheckpoints(simulation, onlyUnfinished=False, onlyCommitted=True)

            time.sleep(interval2)

            for _ in range(workersToDrop1):
                simulation.dropTopWorker()
            for _ in range(workersToAdd1):
                simulation.addWorker()

            self.assertTrue(simulation.waitForHandshake())

            time.sleep(interval3)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
            self.waitForAllCheckpointsToClear(simulation)

            checkpointSecondsElapsed2 = self.totalTimeElapsedOfMostRecentCheckpoints(simulation, onlyUnfinished=False, onlyCommitted=True)

            self.assertTrue(
                checkpointSecondsElapsed2 > checkpointSecondsElapsed,
                "Expected %s to be bigger than %s" % (checkpointSecondsElapsed2, checkpointSecondsElapsed)
                )

            for _ in range(workersToDrop2):
                simulation.dropBottomWorker()
            for _ in range(workersToAdd2):
                simulation.addWorker()

            self.assertTrue(simulation.waitForHandshake())

            time.sleep(interval4)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
            self.waitForAllCheckpointsToClear(simulation)

            checkpointSecondsElapsed3 = self.totalTimeElapsedOfMostRecentCheckpoints(simulation, onlyUnfinished=False, onlyCommitted=True)

            self.assertTrue(
                checkpointSecondsElapsed3 > checkpointSecondsElapsed2,
                "Expected %s to be bigger than %s" % (checkpointSecondsElapsed3, checkpointSecondsElapsed2)
                )
        finally:
            simulation.teardown()

    def test_checkpointingRecoveryFromCorruptedCacheStateOne(self):
        self.checkpointingRecoveryFromCorruptedCacheState(False)

    def test_checkpointingRecoveryFromCorruptedCacheStateAll(self):
        self.checkpointingRecoveryFromCorruptedCacheState(True)

    def checkpointingRecoveryFromCorruptedCacheState(self, deleteAll):
        simulation = self.createSimulation(workerCount=1)
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        viewFactory = simulation.sharedStateViewFactory
        objectStore = simulation.objectStore

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(simpleSumInLoopText)

            time.sleep(5.0)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            self.waitForAllCheckpointsToClear(simulation)

            elapsed = sum(self.timeElapsedOfMostRecentCheckpoints(simulation).values(),0.0)

            print "Total seconds elapsed in computing: ", elapsed

            simulation.dropTopWorker()

            #delete everything in the object store
            keys = simulation.objectStore.listValues()

            if deleteAll:
                logging.info("Deleting all values")
                for k in keys:
                    simulation.objectStore.deleteValue(k[0])
            else:
                toDelete = keys[int(random.random() * len(keys))][0];

                logging.info("Deleting %s of %s", toDelete, keys)

                #delete a random value
                simulation.objectStore.deleteValue(toDelete)

            #give the simulation a couple of seconds to pick a scheduler
            simulation.addWorker()

            self.assertTrue(simulation.waitForHandshake(), "timed out trying to handshake")
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))
            simulation.getGlobalScheduler().setCheckpointStatusInterval(0.1)

            currentRegime = simulation.currentRegime()

            #submit the computation which should trigger an invalid-checkpoint
            #simulation.submitComputation(simpleSumInLoopText)

            #wait until we start making progress again
            time.sleep(5)

            cacheIndex = simulation.getWorkerVdm(0).getPersistentCacheIndex()

            self.assertTrue(len(cacheIndex.allCheckpointedComputationGuids()) == 0)
            self.assertTrue(cacheIndex.totalBytesInCache() == 0)
        finally:
            simulation.teardown()



    def DISABLEDtest_checkpointingAlwaysSuccessful(self):
        simulation = self.createSimulation()
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(sumInLoopText)

            t0 = time.time()

            timestamp = None

            simulation.waitForGlobalScheduler()
            time.sleep(1.0)

            count = 0
            timeOfLastCheckpoint = time.time()
            while time.time() - t0 < 10.0:
                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

                timestamp = self.waitForFullCheckpoint(simulation, priorCheckpoint = timestamp, checkInterval = 0.01)

                statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, True)

                wasSuccessful = statuses[0][1][0].checkpointSuccessful

                self.assertTrue(wasSuccessful)

                for item in simulation.objectStore.listValues():
                    simulation.objectStore.deleteValue(item[0])

                timeOfLastCheckpoint = time.time()

                count += 1

            #make sure we didn't stall either
            self.assertTrue(timeOfLastCheckpoint - time.time() < 5.0)

            print "completed ", count, " checkpoints in 10 seconds."
        finally:
            simulation.teardown()


    def test_checkpointingGarbageCollection(self):
        simulation = self.createSimulation()
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(sumInLoopText)

            t0 = time.time()

            timestamp = None

            simulation.waitForGlobalScheduler()
            time.sleep(1.0)

            count = 0
            timeOfLastCheckpoint = time.time()
            while count < 10:
                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
                self.waitForAllCheckpointsToClear(simulation)
                count += 1

            cache = simulation.getWorkerVdm(0).getPersistentCacheIndex()

            computations = cache.allCheckpointedComputations()

            self.assertTrue(len(computations) == 1)

            checkpoints = cache.checkpointsForComputation(computations[0])

            maxSeconds = 0.0
            for c in checkpoints:
                maxSeconds = max(maxSeconds, cache.checkpointSecondsOfCompute(c))

            time.sleep(2.0)
            simulation.triggerCheckpointGarbageCollection(False)
            time.sleep(2.0)

            checkpoints2 = cache.checkpointsForComputation(computations[0])

            maxSeconds2 = 0.0
            for c in checkpoints2:
                maxSeconds2 = max(maxSeconds, cache.checkpointSecondsOfCompute(c))

            self.assertTrue(len(checkpoints) > 2)
            self.assertEqual(len(checkpoints2), 2)

            #verify we didn't lose the farthest-ahead checkpoint
            self.assertEqual(maxSeconds, maxSeconds2)

        finally:
            simulation.teardown()

    def test_checkpointingGarbageCollectionGraph(self):
        simulation = self.createSimulation()
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            compId1 = simulation.submitComputation(expensiveChildCachecalls(0))
            compId2 = simulation.submitComputation(expensiveChildCachecalls(1))

            simulation.waitForGlobalScheduler()

            time.sleep(1.0)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
            self.waitForAllCheckpointsToClear(simulation)

            cache = simulation.getWorkerVdm(0).getPersistentCacheIndex()

            self.assertTrue(cache.totalComputationsInCache() > 0)
            self.assertEqual(cache.totalReachableComputationsInCache(), 0)

            cache.setScriptDependencies("script", HashNative.ImmutableTreeSetOfHash() + compId1.computationHash)

            self.assertTrue(cache.totalReachableComputationsInCache() > 0)
            self.assertTrue(cache.totalReachableComputationsInCache() < cache.totalComputationsInCache())

            cache.setScriptDependencies("script2", HashNative.ImmutableTreeSetOfHash() + compId2.computationHash)

            self.assertEqual(cache.totalComputationsInCache(), cache.totalReachableComputationsInCache())
        finally:
            simulation.teardown()

    def test_checkpointingGarbageCollectionCleansUpUnusedFiles(self):

        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        simulation = self.createSimulation(s3Service = s3)

        prefix = simulation.objectStore.prefix
        s3().setKeyValue(
            simulation.objectStore.bucketName,
            simulation.objectStore.prefix + "a_file",
            "this is some data"
            )

        s3().setKeyValue(
            "not_the_simulation_object_store_bucket",
            simulation.objectStore.prefix + "a_file",
            "this is some data"
            )

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(expensiveChildCachecalls(0))

            time.sleep(1.0)

            simulation.triggerCheckpointGarbageCollection(False)

            time.sleep(1.0)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            self.waitForAllCheckpointsToClear(simulation)

            self.assertFalse(
                s3().keyExists(
                    simulation.objectStore.bucketName,
                    simulation.objectStore.prefix + "a_file"
                    )
                )

            self.assertTrue(
                s3().keyExists(
                    "not_the_simulation_object_store_bucket",
                    simulation.objectStore.prefix + "a_file"
                    )
                )
        finally:
            simulation.teardown()

    def test_checkpointingAndGarbageCollectionSimultaneously(self):
        simulation = self.createSimulation()
        self.assertTrue(len(simulation.objectStore.listValues()) == 0)

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation(sumInLoopText)

            def injector(*args):
                return .5
            simulation.s3Service.setDelayAfterWriteInjector(injector)

            t0 = time.time()

            timestamp = None

            simulation.waitForGlobalScheduler()
            time.sleep(1.0)

            count = 0
            timeOfLastCheckpoint = time.time()
            for passIx in range(5):
                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
                time.sleep(random.random() * random.random())
                simulation.triggerCheckpointGarbageCollection(False)

                self.waitForAllCheckpointsToClear(simulation)

                totalTime0 = self.totalTimeElapsedOfMostRecentCheckpoints(simulation)

                for ix in range(4):
                    simulation.dropTopWorker()
                for ix in range(4):
                    simulation.addWorker()

                simulation.waitForGlobalScheduler()
                simulation.getGlobalScheduler().setCheckpointStatusInterval(0.01)

                while len(self.timeElapsedOfMostRecentCheckpoints(simulation)) == 0:
                    time.sleep(0.01)

                totalTime1 = self.totalTimeElapsedOfMostRecentCheckpoints(simulation)

                self.assertTrue(totalTime1 >= totalTime0)
        finally:
            simulation.teardown()

    def test_checkpointingWithFaultyWrites(self):
        for injectionType in ["page","bigvec","checkpoint_slice","checkpoint_summary"]:
            print "starting test for injection type ", injectionType

            simulation = self.createSimulation(useHdfsObjectStore=False)
            self.assertTrue(len(simulation.objectStore.listValues()) == 0)

            injectedAnyFailures = [False]
            maxTimesToSee = {'page': 20, 'bigvec': 4, 'checkpoint_slice': 10, 'checkpoint_summary': 1}
            timesToSeeRemaining = [int(maxTimesToSee[injectionType] * random.random())]

            def injector(bucketname, keyname):
                if keyname.endswith(injectionType):
                    if timesToSeeRemaining[0] == 0:
                        timesToSeeRemaining[0] -= 1
                        injectedAnyFailures[0] = True

                        print "injecting a failure in ", injectionType
                        return True
                    else:
                        timesToSeeRemaining[0] -= 1

                return False

            simulation.s3Service.setWriteFailureInjector(injector)

            try:
                #give the simulation a couple of seconds to pick a scheduler
                self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

                simulation.submitComputation(vecOfVecCalcText)

                time.sleep(5.0)

                timestamp = None

                attempt = 0
                hasFailedCheckpoint = False

                while attempt < 10 and not hasFailedCheckpoint:
                    attempt += 1

                    simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

                    timestamp = self.waitForFullCheckpoint(simulation, priorCheckpoint=timestamp)

                    statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, True)

                    wasSuccessful = statuses[0][1][0].checkpointSuccessful

                    if not wasSuccessful:
                        hasFailedCheckpoint = True

                    if injectedAnyFailures[0]:
                        self.assertFalse(wasSuccessful)
                    else:
                        self.assertTrue(wasSuccessful)

                self.assertTrue(hasFailedCheckpoint)

            finally:
                simulation.teardown()

    def test_checkpointStatusSystem(self):
        simulation = self.createSimulation()

        try:
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.getGlobalScheduler().setCheckpointStatusInterval(0.0001)

            simulation.submitComputation(simpleSumInLoopText)

            t0 = time.time()
            complete = False
            lastTimestamp = None
            timestamps = []

            while time.time() < t0 + 10 and not complete:
                if simulation.getAnyResult() is not None:
                    complete = True

                time.sleep(.001)

                statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(True, False)
                if len(statuses):
                    timestamp = statuses[0][1][1].timestamp
                    if timestamp != lastTimestamp:
                        timestamps.append(timestamp)
                        lastTimestamp = timestamp
                else:
                    if timestamps:
                        complete = True

                if (len(timestamps) > 2 and time.time() - lastTimestamp > 1.5) or (lastTimestamp is not None and time.time() - lastTimestamp > 5.0):
                    complete = True

            timestamps.append(time.time())

            intervals = []
            for ix in range(len(timestamps)-1):
                intervals.append(timestamps[ix+1] - timestamps[ix])

            large = [x for x in intervals if x > 2]
            self.assertFalse(large, intervals)

            print "total intervals: ", len(intervals)
        finally:
            simulation.teardown()


    def test_cumulusClientCanCheckpoint(self):
        simulation = self.createSimulation()

        try:
            #give the simulation a couple of seconds to pick a scheduler
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.submitComputation("let v = [1].paged; let res = 0; for ix in sequence(100) res = res + sum(ix, 10**11) + v[0]; res")

            time.sleep(5.0)

            client = simulation.getClient(0)
            client.triggerCheckpoint()
            client = None

            checkpointSecondsElapsed = self.waitForFullCheckpoint(simulation)

            simulation.dropTopWorker()

            self.assertTrue(simulation.waitForHandshake())

            time.sleep(1.0)

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            checkpointSecondsElapsed2 = self.waitForFullCheckpoint(simulation)

            self.assertTrue(
                checkpointSecondsElapsed2 > checkpointSecondsElapsed,
                "Expected %s to be bigger than %s" % (checkpointSecondsElapsed2, checkpointSecondsElapsed)
                )

        finally:
            simulation.teardown()


    def test_checkpointVectorWithSmallPagesInLoop(self):
        simulation = self.createSimulation(useHdfsObjectStore=False)

        try:
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.getGlobalScheduler().setCheckpointStatusInterval(0.01)

            #this computation is designed to produced a bunch of paged vec-within-vec so we
            #can see the system attempting to write a bunch of SyntheticPage objects to long-term
            #storage
            simulation.submitComputation(vecOfVecCalcText)

            complete = False

            lastFullTimestamp = time.time()

            t0 = time.time()

            hasEverTriggered = False

            while time.time() < t0 + 30 and not complete:
                result = simulation.getAnyResult()
                if result is not None:
                    complete = True
                else:
                    time.sleep(1.0)

                    if not hasEverTriggered:
                        if self.timestampOfMostRecentCheckpoint(simulation) is not None:
                            hasEverTriggered = True
                            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()
                    else:
                        ts = self.timestampOfMostRecentFullCheckpoint(simulation)

                        if ts is not None:
                            if lastFullTimestamp < ts:
                                totalBytes = sum([i[1] for i in simulation.objectStore.listValues()])
                                print "took ", ts - lastFullTimestamp, ". total bytes = ", totalBytes
                                lastFullTimestamp = ts
                                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            #make sure we're still able to reliably checkpoint
            self.assertLess(time.time() - lastFullTimestamp, 8.0)
        finally:
            simulation.teardown()

    def printRepeatedCheckpointStatusInfo(self, statusLists):
        ix = 0
        for statusList in statusLists:
            print "Pass ", ix

            microPass = 0
            for statuses in statusList:
                print "\tMicropass ", microPass
                for c in statuses:
                    print "\t\t", "%.2f" % statuses[c], " for ", c
                microPass += 1
            ix = ix + 1

    def test_checkpointLoadDirectlyFromCacheBasic1(self):
        checkpointRegimes = self.loadCheckpointFromFreshSimulationTest(vecOfVecCalcText, [2,4])

        self.printRepeatedCheckpointStatusInfo(checkpointRegimes)

        self.validateSingleIncreasingComputationTimestamp(checkpointRegimes)

    def test_checkpointLoadDirectlyFromCacheBasic2(self):
        #verify that over many passes of add/drop we see steadily increasing timestamps
        checkpointRegimes = self.loadCheckpointFromFreshSimulationTest(bigSumText, [3,3,3,3,3,3])

        self.printRepeatedCheckpointStatusInfo(checkpointRegimes)

        self.validateSingleIncreasingComputationTimestamp(checkpointRegimes)

    def test_checkpointLoadDirectlyFromCacheBasicMultipleClients(self):
        #verify that over many passes of add/drop we see steadily increasing timestamps
        checkpointRegimes = self.loadCheckpointFromFreshSimulationTest(bigSumText, [3,3,3,3,3,3], clientCount=3)

        self.printRepeatedCheckpointStatusInfo(checkpointRegimes)

        self.validateSingleIncreasingComputationTimestamp(checkpointRegimes)

    def test_checkpointLoadDirectlyFromCacheWithCachecalls(self):
        self.validateSingleIncreasingComputationTimestamp(
            self.loadCheckpointFromFreshSimulationTest(cachedBigSumText, [4,4])
            )

    def validateSingleIncreasingComputationTimestamp(self, checkpointRegimes):
        #we should see a single computation with its timestamp steadily increasing
        index = 0
        for regime in checkpointRegimes:
            if index > 0:
                lastSample = regime[-1]
                comps = [lastSample[c] for c in lastSample if lastSample[c] > .1]
                self.assertTrue(len(comps) == 1, "Expected 1 comp. Had %s at index %s" % (len(comps), index))
            index += 1

        for ix in range(len(comps)-1):
            self.assertTrue(comps[ix+1] > comps[ix])

    def loadCheckpointFromFreshSimulationTest(self, calculationText, timestampsPerPassList, clientCount=1, timestep = 1.0):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        statuses = []
        viewFactory = None

        for timestampsThisPass in timestampsPerPassList:
            simulation = InMemoryCumulusSimulation.InMemoryCumulusSimulation(
                4, #worker count
                clientCount,
                memoryPerWorkerMB=100,
                threadsPerWorker=2,
                s3Service=s3,
                sharedStateViewFactory=viewFactory
                )

            viewFactory = simulation.sharedStateViewFactory

            statusesThisPass = []

            try:
                self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

                simulation.getGlobalScheduler().setCheckpointStatusInterval(0.1)

                for ix in range(clientCount):
                    simulation.submitComputationOnClient(ix, calculationText)

                for subPass in range(timestampsThisPass):
                    time.sleep(timestep)
                    statusesThisPass.append(self.timeElapsedOfMostRecentCheckpoints(simulation))

                simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

                self.waitForFullCheckpoint(simulation)

                statusesThisPass.append(self.timeElapsedOfMostRecentCheckpoints(simulation))
            finally:
                for ix in range(4):
                    simulation.getWorker(ix).dumpStateToLog()

                simulation.teardown()

            statuses.append(statusesThisPass)

        return statuses


    def DISABLEDtest_canTriggerCheckpointOfCompleted(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        simulation = InMemoryCumulusSimulation.InMemoryCumulusSimulation(
            4, #worker count
            1,
            memoryPerWorkerMB=100,
            threadsPerWorker=2,
            s3Service=s3
            )

        try:
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.waitForHandshake()

            simulation.submitComputation("1+2")

            result = simulation.waitForAnyResult()

            self.assertTrue(result.isResult())

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            ts = self.waitForFullCheckpoint(simulation, onlyUnfinished=False)

            self.assertTrue(ts is not None)

            statuses = simulation.getGlobalScheduler().currentOutstandingCheckpointStatuses(False, False)

            status = statuses[0]
            compId = status[0]
            checkpointStatus = status[1][0]
            checkpointRequest = status[1][1]

            #verify that it's a storage checkpoint
            self.assertTrue(checkpointRequest.writeToStorage)
            self.assertTrue(checkpointStatus.checkpointSuccessful)
            self.assertTrue(checkpointStatus.isRootComputationFinished)
        finally:
            simulation.teardown()

    def test_dependingOnCheckpointedFinishedCachecallWorks(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        simulation = InMemoryCumulusSimulation.InMemoryCumulusSimulation(
            4, #worker count
            1,
            memoryPerWorkerMB=100,
            threadsPerWorker=2,
            s3Service=s3
            )

        try:
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.waitForHandshake()

            baseComp = simulation.createComputation("1+2")
            baseCompId = simulation.getClient(0).createComputation(baseComp)

            simulation.getClient(0).setComputationPriority(baseCompId, CumulusNative.ComputationPriority(1))

            result = simulation.waitForAnyResult()
            self.assertTrue(result.isResult())

            simulation.getGlobalScheduler().triggerFullCheckpointsOnOutstandingComputations()

            self.waitForAllCheckpointsToClear(simulation)

            for ix in range(100):
                childComp = simulation.createComputation("x + %s" % ix, x=baseComp)
                childCompId = simulation.getClient(0).createComputation(childComp)
                simulation.getClient(0).setComputationPriority(childCompId, CumulusNative.ComputationPriority(1))

                result = simulation.waitForAnyResult()
        finally:
            simulation.teardown()


    def test_cumulusCanTriggerNewRegimes(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        simulation = InMemoryCumulusSimulation.InMemoryCumulusSimulation(
            4, #worker count
            1,
            memoryPerWorkerMB=100,
            threadsPerWorker=2,
            s3Service=s3
            )

        try:
            self.assertTrue(simulation.waitForGlobalScheduler(timeout=2.0))

            simulation.waitForHandshake()
            regime = simulation.getWorker(0).getRegimeHash()
            self.assertTrue(regime is not None)

            simulation.getWorker(0).triggerRegimeChange()

            time.sleep(1.0)

            simulation.waitForHandshake()

            regime2 = simulation.getWorker(0).getRegimeHash()
            self.assertTrue(regime2 is not None)
            self.assertTrue(regime2 != regime)
        finally:
            simulation.teardown()

