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

import time
import numpy

import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.ForaValue as ForaValue
import ufora.BackendGateway.ComputedValue.ComputedValue as ComputedValue
import ufora.util.Teardown as Teardown
import ufora.BackendGateway.ComputedGraph.BackgroundUpdateQueue as BackgroundUpdateQueue
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway

class ComputedValueTestCases(object):
    def waitUntilTrue(self, predicate, timeout = 10.0):
        t0 = time.time()
        interval = 0.001
        while not predicate():
            time.sleep(interval)

            BackgroundUpdateQueue.pullOne(timeout = interval)
            self.graph.flush()

            if time.time() - t0 > timeout:
                self.assertFalse(True, "timed out")
                return

            interval = min(interval * 2, 0.1)

    def verifyIsInterruptible(self, longRunningComputationText, minWorkerCount):
        x = createComputedValue(longRunningComputationText, "`Call")

        with IncreasedRequestCount(x):
            tries = 0
            finished = False

            while not finished and tries < 100:
                refreshGraph(self.graph)
                time.sleep(.1)
                refreshGraph(self.graph)

                if x.totalWorkerCount >= minWorkerCount:
                    finished = True
                else:
                    tries = tries + 1

            self.assertTrue(finished, "Couldn't get enough workers")

        finished = False
        tries = 0

        while not finished and tries < 100:
            time.sleep(.1)
            refreshGraph(self.graph)

            if x.totalWorkerCount == 0:
                finished = True
            else:
                tries = tries + 1

        self.assertTrue(finished, "Couldn't interrupt the workers!")

    def timeComputation(self, computation):
        t0 = time.time()
        with IncreasedRequestCount(computation):
            while computation.valueIVC is None:
                time.sleep(.1)
                refreshGraph(self.graph)
            return time.time() - t0

    def timeComputationWithFrequentInterrupts(self, computation, timeout):
        t0 = time.time()
        timeout = max(timeout, 5)
        timeoutPoint = time.time() + timeout

        while computation.valueIVC is None:
            assert time.time() < timeoutPoint

            with IncreasedRequestCount(computation):
                time.sleep(.1)

                refreshGraph(self.graph)

        return time.time() - t0

    def verifyIsResumable(self, computedValueGenerator):
        #test that we can stop a computation and restart it and not start over
        calcTime1 = self.timeComputation(computedValueGenerator())
        calcTime2 = self.timeComputation(computedValueGenerator())
        calcTime3 = self.timeComputation(computedValueGenerator())

        x = computedValueGenerator()

        #first, compute a bit of it
        with IncreasedRequestCount(x):
            time.sleep(calcTime3 * .25)

        refreshGraph(self.graph)

        self.assertTrue(
            x.valueIVC is None,
            "%s was expected to be None. Caltimes were %s, %s, %s" % (
                str(x.valueIVC),
                calcTime1,
                calcTime2,
                calcTime3
                )
            )

        #Verify that it doesn't complete if we just wait
        time.sleep(calcTime3 * 1.5)

        refreshGraph(self.graph)

        self.assertTrue(
            x.valueIVC is None,
            "%s was expected to be None. Caltimes were %s, %s, %s" % (
                str(x.valueIVC),
                calcTime1,
                calcTime2,
                calcTime3
                )
            )

        #now compute it a little bit at a time and verify that we g to the
        #end. if resumption is broken, this should never complete
        remainingTime = self.timeComputationWithFrequentInterrupts(x, timeout = calcTime3 * 5)

        self.assertTrue(remainingTime < calcTime3 * 2.0,
            "took %s, which I expected to be around %s but wasn't" % (
                remainingTime,
                calcTime3 * .75
                )
            )

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_evaluation_works(self):
        x = createComputedValue("fun(x){x+1}", "`Call", "2")
        waitForResult(self.graph, x)
        self.assertEqual(x.valueIVC.pyval, 3)

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_stringification_of_NAN(self):
        x = createComputedValue("fun(){`log(-10)}", "`Call")
        waitForResult(self.graph, x)
        self.assertEqual(str(x.valueIVC), "nan")

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_splittingWorks(self):
        for passIndex in range(10):
            x = createComputedValue("fun() { sum(0,1000000000 + %s) }" % passIndex, "`Call")
            maxCPUs = waitForResult(self.graph, x)
            if maxCPUs > 1:
                return

        self.assertTrue(False, "Never got more than 1 CPU")

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_valsAreHashable(self):
        x = createComputedValue("fun() { sum(0,1000000000) }", "`Call")
        x.hash

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_computationIsInterruptible_1(self):
        self.verifyIsInterruptible("fun() { let x = 0; while (true) { x = x + 1 } }", 1)

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_computationIsInterruptible_2(self):
        self.verifyIsInterruptible("fun() { sum(0,10**14) }", 2)

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_computationIsResumable(self):
        ct = [0]
        def generateExample():
            ct[0] += 1
            return createComputedValue(
                "let c = %s;" % ct[0] +
                    "let f = fun(ix) { ix + c };" +
                    "fun() { let res = nothing; for c in sequence(5 * 10**8) res = res + f(c) }",
                "`Call"
                )


        self.verifyIsResumable(generateExample)

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_CacheLoader(self):
        x = createComputedValue("fun() { Vector.range(100) }", "`Call")
        waitForResult(self.graph, x)
        vecCacheItem = x.asVector

        vecCacheItem = vecCacheItem.entireSlice

        with IncreasedRequestCount(vecCacheItem):
            waitCacheItemIsLoaded(self.graph, vecCacheItem)
            leafData = vecCacheItem.extractVectorDataAsNumpyArray()
            self.assertTrue((leafData == numpyRange(100)).all())

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_CacheLoader_2(self):
        for i in range(1000):
            x = createComputedValue("fun() { Vector.range(100) }", "`Call")
            waitForResult(self.graph, x)
            vecCacheItem = x.asVector

            vecCacheItem = vecCacheItem.entireSlice

            with IncreasedRequestCount(vecCacheItem):
                waitCacheItemIsLoaded(self.graph, vecCacheItem)
                leafData = vecCacheItem.extractVectorDataAsNumpyArray()
                self.assertTrue((leafData == numpyRange(100)).all())

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_CacheLoader_paged_1(self):
        for i in range(1,100):
            for j in range(10):
                x = createComputedValue("fun() { Vector.range(%s).paged }" %i, "`Call")
                waitForResult(self.graph, x)
                vecCacheItem = x.asVector

                vecCacheItem = vecCacheItem.entireSlice

                with IncreasedRequestCount(vecCacheItem):
                    waitCacheItemIsLoaded(self.graph, vecCacheItem)
                    leafData = vecCacheItem.extractVectorDataAsNumpyArray()
                    self.assertTrue((leafData == numpyRange(i)).all())




    @Teardown.Teardown
    def test_unit_L2_ComputedValue_CacheLoader_sliced(self):
        x = createComputedValue("fun() { Vector.range(100) }", "`Call")
        waitForResult(self.graph, x)
        xAsVector = x.asVector

        xSliced = xAsVector[0:25:1]

        waitForResult(self.graph, xSliced)

        xSlicedAsVector = xSliced.asVector

        vecSlice = xSlicedAsVector.entireSlice

        with IncreasedRequestCount(vecSlice):
            waitCacheItemIsLoaded(self.graph, vecSlice)
            leafData = vecSlice.extractVectorDataAsNumpyArray()
            self.assertTrue((leafData == numpyRange(25)).all())

    @Teardown.Teardown
    def test_unit_L2_ComputedValue_CacheLoader_sliced_paged(self):
        for i in range(1000):
            x = createComputedValue("fun() { Vector.range(100).paged }", "`Call")
            waitForResult(self.graph, x)
            xAsVector = x.asVector

            xSliced = xAsVector[0:25:1]

            waitForResult(self.graph, xSliced)

            xSlicedAsVector = xSliced.asVector

            vecSlice = xSlicedAsVector.entireSlice

            with IncreasedRequestCount(vecSlice):
                waitCacheItemIsLoaded(self.graph, vecSlice)
                leafData = vecSlice.extractVectorDataAsNumpyArray()
                self.assertTrue((leafData == numpyRange(25)).all())

    @Teardown.Teardown
    def test_dependentComputedValue(self):
        fastTimes = []
        slowTimes = []

        for ix in range(5):
            coreComp = createComputedValue("fun() { let x = %s; let y = 0; while(x<3000000000) {x=x+1;y=y+x}; y }" % ix, "`Call")
            childComp = createComputedValue(coreComp, "`Operator", "`+", "1")

            t0 = time.time()
            waitForResult(self.graph, coreComp)
            t1 = time.time()
            waitForResult(self.graph, childComp)
            t2 = time.time()

            fastTime = t2 - t1
            slowTime = t1 - t0

            fastTimes.append(fastTime)
            slowTimes.append(slowTime)

        mid = len(fastTimes) / 2
        fastTime = fastTimes[mid]
        slowTime = slowTimes[mid]

        self.assertTrue(fastTime < slowTime / 6,
            "Fast/Slow times were %s and %s. Expected the first to be much faster than the second." % (
                fastTimes,
                slowTimes
                )
            )

    @Teardown.Teardown
    def test_coresOnDependentValuesCorrect(self):
        cur = "10**9"
        common = createComputedValue("fun(x) { x  }", "`Call", "`Call")
            
        comps = []
        vis = []
        for ix in range(10):
            cur = createComputedValue("fun(x) { let res = x; let ct = 10**9; while (ct>0) { res = res + 1; ct = ct - 1} res  }", common, cur)
            comps.append(cur)
            v = createComputedValue("fun(x) { x }", "`Call", cur)
            v = createComputedValue("fun(x) { x }", "`Call", v)

            vis.append(v)

        ix = 0
        for c in comps:
            ix += 1

        with IncreasedRequestCount(comps):
            pass

        with IncreasedRequestCount(vis):
            for c in vis:
                self.waitUntilTrue(lambda: c.totalWorkerCount == 1)
            
    @Teardown.Teardown
    def test_checkpointingFinishedComputationsReceivesStats(self):
        readComp = createComputedValue("fun() { sum(0,10**10) }", "`Call")

        readComp.increaseRequestCount()

        waitForResult(self.graph, readComp)

        readComp.requestComputationCheckpoint()

        t0 = time.time()

        while time.time() - t0 < 10.0:
            time.sleep(.1)
            refreshGraph(self.graph)

            stats = readComp.checkpointStatus

            if stats.isRootComputationFinished and readComp.isCompletelyCheckpointed:
                return
            

        self.assertTrue(False, "Timed out without ever producing a valid checkpoint.")


    @Teardown.Teardown
    def test_statsAllocateTimeSpentCorrectly(self):
        expensiveComp = createComputedValue("fun() { sum(0,5*10**10) }", "`Call")
        simpleComp1 = createComputedValue("fun(x) { x + 1 }", "`Call", expensiveComp)
        simpleComp2 = createComputedValue("fun(x) { x + 2 }", "`Call", expensiveComp)
        simpleComp3 = createComputedValue("fun(x) { x + 3 }", "`Call", expensiveComp)
        simpleComps = [simpleComp1, simpleComp2, simpleComp3]

        #ensure that we have a ComputationId for expensiveComp, so that later we can
        #request that it be checkpointed
        with IncreasedRequestCount([expensiveComp]):
            time.sleep(.1)

        with IncreasedRequestCount(simpleComps):
            waitForResults(self.graph, simpleComps)

            self.waitUntilTrue(lambda: simpleComp1.checkpointStatus is not None)
            self.waitUntilTrue(lambda: simpleComp2.checkpointStatus is not None)
            self.waitUntilTrue(lambda: simpleComp3.checkpointStatus is not None)

            time.sleep(2.0)
            refreshGraph(self.graph)

            spentALongTime = 0
            hasMemory = 0

            for c in simpleComps:
                if c.checkpointStatus.statistics.timeSpentInCompiler > 1.0:
                    spentALongTime += 1
                if c.checkpointStatus.statistics.totalBytesInMemory > 0:
                    hasMemory += 1

            self.assertEqual(spentALongTime, 1)
            self.assertEqual(hasMemory, 3)

            expensiveComp.requestComputationCheckpoint()

            self.waitUntilTrue(lambda: 
                simpleComp1.totalComputeSecondsAtLastCheckpoint > 0.0 or
                simpleComp2.totalComputeSecondsAtLastCheckpoint > 0.0 or
                simpleComp3.totalComputeSecondsAtLastCheckpoint > 0.0,
                timeout=30.0
                )



    #this exposes a bug we have
    @Teardown.Teardown
    def DISABLEDtest_memoryLoadForSequentialComputations(self):
        v0 = createComputedValue("fun() { Vector.range(1000000).paged }", "`Call")
        vs = [v0]

        for ix in range(10):
            v0 = createComputedValue("fun(v) { (v ~~ {_+1}).paged }", "`Call", v0)
            vs.append(v0)

        with IncreasedRequestCount(vs):
            waitForResults(self.graph, vs)

            time.sleep(2.0)
            refreshGraph(self.graph)

            for v in vs:
                self.waitUntilTrue(lambda: v.totalBytesOfMemoryReferenced > 1000000)
                print v.totalBytesOfMemoryReferenced

            for v in vs:
                #ensure we're not double counting the input and output vectors
                self.assertTrue(v.totalBytesOfMemoryReferenced < 10000000, v.totalBytesOfMemoryReferenced)





def refreshGraph(graph):
    BackgroundUpdateQueue.pullAll()
    graph.flush()

def createComputedValue(*strings):
    return ComputedValue.ComputedValue(
        args=tuple([
            (FORA.extractImplValContainer(
                ForaValue.FORAValue(FORA.eval(x))
                ) if isinstance(x, str) else x)
                for x in strings
                ])
        )

def waitForResult(graph, x, timeout = 60.0):
    return waitForResults(graph, [x], timeout)

def waitForResults(graph, values, timeout = 60.0):
    """wait for 'x' to have 'result' not be zero. return the maximum number
    of CPUs ever observed to be allocated to 'x'"""
    t0 = time.time()

    def notLoadedCount():
        notLoadedCount = 0

        for x in values:
            if x.valueIVC is None:
                notLoadedCount += 1

        return notLoadedCount

    with IncreasedRequestCount(values):
        maxCPUs = None
        while notLoadedCount() > 0 and time.time() - t0 < timeout:
            time.sleep(.01)
            BackgroundUpdateQueue.pullOne(timeout = .10)
            graph.flush()

            for x in values:
                if x.totalWorkerCount is not None:
                    if maxCPUs is None:
                        maxCPUs = x.totalWorkerCount
                    else:
                        maxCPUs = max(maxCPUs,x.totalWorkerCount)

        assert notLoadedCount() == 0, "Timed out: %s of %s didn't finish:\n\t%s\n" % (
            notLoadedCount(),
            len(values),
            "\n\t".join(
                [str(x) for x in values if x.valueIVC is None]
                )
            )

        return maxCPUs

def numpyRange(ct):
    return numpy.ones(ct).cumsum() - 1

def waitCacheItemIsLoaded(graph, cacheItem):
    with IncreasedRequestCount(cacheItem):
        while not cacheItem.isLoaded:
            BackgroundUpdateQueue.pullOne()
            graph.flush()

def waitCacheItemsAreLoaded(graph, cacheItems, timeout = 60.0):
    with IncreasedRequestCount(cacheItems):
        def allAreLoaded():
            for c in cacheItems:
                if not c.isLoaded:
                    return False

            return True

        t0 = time.time()

        while not allAreLoaded() and time.time() - t0 < timeout:
            BackgroundUpdateQueue.pullOne(timeout = 1.0)
            graph.flush()

        assert allAreLoaded(), "Timed out"

class IncreasedRequestCount(object):
    def __init__(self, request):
        self.request = request

    def __enter__(self):
        if not isinstance(self.request, list):
            self.request.increaseRequestCount()
        else:
            for l in self.request:
                l.increaseRequestCount()

    def __exit__(self, *args):
        if not isinstance(self.request,list):
            self.request.decreaseRequestCount()
        else:
            for l in self.request:
                l.decreaseRequestCount()

