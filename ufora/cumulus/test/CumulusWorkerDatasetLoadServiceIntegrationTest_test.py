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
import logging
import numpy
import ufora.native.Cumulus as CumulusNative
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.TCMalloc as TCMallocNative
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import cPickle as pickle

callbackScheduler = CallbackScheduler.singletonForTesting()

class CumulusWorkerDatasetLoadServiceIntegrationTest(unittest.TestCase):
    def assertBecomesTrueEventually(self, f, timeout, msgFun):
        t0 = time.time()
        while not f():
            time.sleep(.1)
            if time.time() - t0 > timeout:
                self.assertTrue(False, msgFun())

    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    def test_PythonIoTaskService(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        for ix1 in range(20):
            for ix2 in range(20):
                s3().setKeyValue(
                    "bucketname",
                    "key_%s_%s" % (ix1, ix2),
                    "".join(
                        ("%s,%s,%s\n" % (ix1, ix2, ix3) for ix3 in range(1024))
                        )
                    )

        text = """
            String(
                [parsing.csv(datasets.s3('bucketname', 'key_%s'.format(ix)), hasHeaders: false)
                    .data[512]
                    for ix in sequence(20)
                    ]
                )
            """

        self.assertIsNotNone(self.computeUsingSeveralWorkers(text, s3, 1))

    def test_PythonIoTaskService2(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        for ix1 in range(20):
            for ix2 in range(20):
                s3().setKeyValue(
                    "bucketname",
                    "key_%s_%s" % (ix1, ix2),
                    "".join(
                        ("%s,%s,%s\n" % (ix1, ix2, ix3) for ix3 in range(1024))
                        )
                    )

        text = """
            datasets.s3('bucketname', 'key_0').dataAsString
            """

        self.assertIsNotNone(self.computeUsingSeveralWorkers(text, s3, 1))

    def DISABLEDtest_PythonIoTaskService3(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        s3.setThroughputPerMachine(1024 * 1024 * 20)

        for ix in range(35):
            s3().setKeyValue(
                "bucketname",
                "key_%s" % ix,
                " " * 10 * 1024 * 1024
                )

        text = """
            datasets.s3('bucketname', 'key').sum()
            """

        self.assertIsNotNone(self.computeUsingSeveralWorkers(text, s3, 4, timeout = 120, blockUntilConnected=True))

        totalBytecount = 0
        for machine, bytecount in s3.getPerMachineBytecounts().iteritems():
            totalBytecount += bytecount

        self.assertTrue(totalBytecount / 1024 / 1024 <= 500, totalBytecount / 1024 / 1024)

    def test_PythonIoTaskServiceInLoop(self):
        bytesUsed = []
        for ix in range(20):
            bytesUsed.append(TCMallocNative.getMemoryStat("generic.current_allocated_bytes") / 1024 / 1024.0)

            s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

            s3.setThroughputPerMachine(1024 * 1024 * 20)

            for ix in range(35):
                s3().setKeyValue(
                    "bucketname",
                    "key_%s" % ix,
                    " " * 10 * 1024 * 1024
                    )

            text = """datasets.s3('bucketname', 'key_0').sum()"""

            self.computeUsingSeveralWorkers(text, s3, 4, timeout = 120, blockUntilConnected=True)

        self.assertTrue(bytesUsed[0] < bytesUsed[-1] - 100, bytesUsed)


    def dataCreationTest(self, totalMB, workers = 1, threadsPerWorker = 4):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """size(Vector.range(%s, {_*_}))""" % (totalMB * 1024 * 1024 / 8)

        self.assertIsNotNone(
            self.computeUsingSeveralWorkers(
                text,
                s3,
                workers,
                timeout = 120,
                memoryLimitMb=totalMB / workers * 1.3,
                threadCount = threadsPerWorker,
                useInMemoryCache = False
                )
            )


    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.0500_MB_1Worker")
    def test_createData_500_1(self):
        self.dataCreationTest(500)
    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.1000_MB_1Worker")
    def test_createData_1000_1(self):
        self.dataCreationTest(1000)
    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.2000_MB_1Worker")
    def test_createData_2000_1(self):
        self.dataCreationTest(2000)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.0500_MB_2Workers")
    def test_createData_500_2(self):
        self.dataCreationTest(500, 2, 2)
    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.1000_MB_2Workers")
    def test_createData_1000_2(self):
        self.dataCreationTest(1000, 2, 2)
    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorRange.2000_MB_2Workers")
    def test_createData_2000_2(self):
        self.dataCreationTest(2000, 2, 2)


    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.DataFanout")
    def test_DataFanout(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let v = [[x].paged for x in sequence(8)]

            let q = v ~~ { let r = 0; for ix in sequence(10**8.5) r = r + _[0]; r }

            q.sum()
            """

        self.assertIsNotNone(self.computeUsingSeveralWorkers(text, s3, 4, timeout = 120))

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.LargeCSVParse")
    def test_LargeCSVParse(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        for ix1 in range(10):
            s3().setKeyValue(
                "bucketname",
                "key_%s" % ix1,
                "".join(
                    ("%s,%s,%s\n" % (ix1, ix2, ix1 * ix2) for ix2 in range(100000))
                    )
                )

        text = """
            let dataset = datasets.s3('bucketname', 'key');

            size(parsing.csv(dataset, hasHeaders: false))
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4, memoryLimitMb=800, timeout=120)

        self.assertTrue(res.isResult(), res)
        self.assertEqual(res.asResult.result.pyval, 10 * 100000)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.CreateManySmallVectors")
    def test_CreateManySmallVectors(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let v = []; for ix in sequence(1000000) { v = v + [ix] }; v.sum()
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4)

        self.assertTrue(res.isResult())

        self.assertEqual(res.asResult.result.pyval, 499999500000)

    def test_CalculateWithCachecallsFirst(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let f = fun(ix) { fun(a) { a * ix } };
            let g = fun(ix) { sum(0,10**9, f(ix)) };

            //first, do a papply so that we have some cachenodes in the system
            let res1 = Vector.range(4).apply(fun(ix) { cached(g(ix))[0] + 1 });

            //now repeat the calculation with non-papply nodes
            let res2 = Vector.range(4).apply(fun(ix) { g(ix) + 1 });

            if (res1 == res2)
                return "OK"
            else
                return "%s != %s".format(res1, res2)
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4, timeout=30)

        self.assertIsNotNone(res)
        self.assertTrue(res.isResult())
        self.assertEqual(res.asResult.result.pyval, "OK")


    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.CachecallsAndVectors")
    def test_CachecallsAndVectors(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let sumVec = fun(v) { v.sum() };

            let v2 = Vector.range(100).papply(fun(ix) {
                let v = Vector.range(ix).paged;
                cached(sumVec(v))[0]
                });

            let v3 = [sum(0,ix) for ix in sequence(100)];

            if (v2 == v3) "OK" else (String(v2),String(v3))
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4, timeout=20)

        self.assertTrue(res.isResult())
        self.assertEqual(res.asResult.result.pyval, "OK")

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.VectorsAndSums")
    def test_VectorsAndSums(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let v = Vector.range(100).apply(fun(ix) {
                [ix * x for x in sequence(10000)].paged
                })

            v.sum(fun(vElt) { sum(0, 10**7) + vElt.sum() })
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4, timeout=20)

        self.assertTrue(res.isResult(), res)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.ParseRowsAsFloatVectors")
    def test_ParseRowsAsFloatVectors(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        rows = 10000

        bucketData = "\n".join(
                [",".join([str(((x * row) **2) % 503) for x in range(200)]) for row in range(rows)]
                )

        s3().setKeyValue(
            "bucketname",
            "key",
            bucketData
            )

        text = """
            let bytes = datasets.s3('bucketname', 'key');

            let rows = bytes.split(fun(x){x == 10});

            let parsed = rows.apply(fun(row) {
                row.split(
                    fun(x) { x == ','[0] },
                    fun(x) { Float64(x.dataAsString) }
                    )
                })

            size(parsed)
            """

        res = self.computeUsingSeveralWorkers(text, s3, 4, timeout=30)

        self.assertTrue(res.isResult(), res)
        self.assertEqual(res.asResult.result.pyval, rows)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.ParseRowsAsFloatTuples")
    def test_ParseRowsAsFloatTuples(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        rows = 10000

        bucketData = "\n".join(
                [",".join([str(((x * row) **2) % 503) for x in range(200)]) for row in range(rows)]
                )

        s3().setKeyValue(
            "bucketname",
            "key",
            bucketData
            )

        text = """
            let bytes = datasets.s3('bucketname', 'key');

            let df = parsing.csv(bytes, hasHeaders: false, defaultColumnType: Float64)

            size(df)
            """

        t0 = time.time()
        parsedInPython2 = [[float(x) for x in row.split(",")] for row in bucketData.split("\n")]
        pythonTime = time.time() - t0

        t0 = time.time()
        res = self.computeUsingSeveralWorkers(text, s3, 4, memoryLimitMb = 800, timeout=60)
        foraTime = time.time() - t0

        t0 = time.time()
        res = self.computeUsingSeveralWorkers(text, s3, 4, memoryLimitMb = 800, timeout=60)
        foraTime2 = time.time() - t0

        self.assertTrue(res.isResult(), res)
        self.assertEqual(res.asResult.result.pyval, rows)

        print "FORA1: %s. FORA2: %s. Python %s. Ratio: %s" % (foraTime, foraTime2, pythonTime, foraTime / pythonTime)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.LargeVectorRange")
    def test_largeVectorRange(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        res = self.computeUsingSeveralWorkers("""
            let res = 0;
            for ix in sequence(10) {
                let v1 = Vector.range(50000000);
                res = res + size(v1);
                }
            res
            """, s3, 4, timeout = 200)

        if res.isResult():
            self.assertEqual(res.asResult.result.pyvalOrNone, 50000000 * 10, res)
        else:
            self.assertTrue(False, res)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.SortLargeVectorRange")
    def test_sortLargeVectorRange(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        for ix in range(2):
            t0 = time.time()
            self.computeUsingSeveralWorkers("""
                let v = Vector.range(4 * 1000 * 1000, fun(ix) { (ix ** 1.2 % 20.0, ix) } );
                sort(v)

                """,
                s3,
                4,
                timeout = 120
                )
            foraTime = time.time() - t0

        t0 = time.time()
        v = [ (ix ** 1.2 % 20.0, ix) for ix in range(4 * 1000 * 1000) ]
        v = sorted(v)
        pyTime = time.time() - t0

        print "pyTime: %s, foraTime: %s, ratio: %s" % (pyTime, foraTime, pyTime / foraTime)

    def test_sortVec2(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result = self.computeUsingSeveralWorkers("""
            let v = Vector.range(50000, fun(ix) { ix  / 10 } );
            sorting.isSorted(sort(v))
            """, s3, 4)

        self.assertEqual(result.asResult.result.pyval, True)

    def test_performManySums(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        for ix in range(2):
            t0 = time.time()
            self.computeUsingSeveralWorkers("""
                let v = Vector.range(4 * 1000 * 1000);

                sum(0,100, fun(ix) {
                    v.sum(fun(vElt) { vElt + ix })
                    })
                """, s3, 4
                )
            foraTime = time.time() - t0

        t0 = time.time()
        v = numpy.ones(4000000).cumsum() - 1
        for ix in range(100):
            (v+ix).sum()
        pyTime = time.time() - t0

        print "pyTime: %s, foraTime: %s, ratio: %s" % (pyTime, foraTime, pyTime / foraTime)

    def test_computeManyGetitems(self):
        #verify that the compiler doesn't crap out during many runs.
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        interpreterTimes = []

        for ix in range(10):
            interpTime = self.computeUsingSeveralWorkers("""
                    let f = fun(x){x+x+x+x+x}
                    let v = [f((x+1,x+2,x-10,x)) for x in sequence(4000)];

                    let res = 0;
                    let r = %s + 0;

                    for ix in sequence(1) {
                        res = res + Vector.range(size(v[0])).sum(fun(ix) {
                            v.sum(fun(x){x[ix]+r})
                            })
                        }

                    res
                    """ % ix, s3, 1, wantsStats = True, timeout=240
                    )[1].timeSpentInInterpreter

            interpreterTimes.append(interpTime)

        for interpTime in interpreterTimes[1:]:  # ignoring the first run
            self.assertLess(interpTime, (sum(interpreterTimes) - interpTime) / (len(interpreterTimes) - 1) * 10)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.gcOfPagedVectors")
    def test_gcOfPagedVectors(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        self.computeUsingSeveralWorkers("""
            let res = 0

            for ix in sequence(100) {
                res = res + Vector.range(1000000+ix).paged.sum()
                }

            res
            """, s3, 4, timeout=240
            )


    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.produceLotsOfData")
    def test_produceLotsOfData(self):
        #verify that the compiler doesn't crap out during many runs.
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers("""
                let v = []

                for ix in sequence(50*1000*1000)
                    v = v :: ix

                v
                """, s3, 4, timeout=240, returnSimulation=True
                )
        try:
            def test():
                for worker, vdm, eventHandler in simulation.workersVdmsAndEventHandlers:
                    self.assertTrue(
                        vdm.curTotalUsedBytes() < 150 * 1024 * 1024,
                        "We are using %s >= 150MB" % (vdm.curTotalUsedBytes() / 1024 / 1024.0)
                        )
            test()
        finally:
            simulation.teardown()



    def test_schedulerEventsAreSerializable(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers("""
                sum(0,10**10)
                """, s3, 4, timeout=240, returnSimulation=True
                )

        try:
            someHadEvents = False

            for worker, vdm, eventHandler in simulation.workersVdmsAndEventHandlers:
                events = eventHandler.extractEvents()

                events2 = pickle.loads(pickle.dumps(events))

                print len(events), "events"
                print len(pickle.dumps(events)), " bytes"
                print len(pickle.dumps(events)) / len(events), " bytes per event."

                self.assertTrue(len(events2) == len(events))

                if len(events):
                    someHadEvents = True

                CumulusNative.replayCumulusWorkerEventStream(events, True)

            self.assertTrue(someHadEvents)

            worker = None
            vdm = None
            eventHandler = None
        except Exception as e:
            import traceback
            logging.error("exception: %s", traceback.format_exc())
            raise
        finally:
            simulation.teardown()

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.fanout")
    def test_fanout_1(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        self.computeUsingSeveralWorkers("""
            let v = Vector.range(10000000)

            v.sum()

            let isPrime = fun(p) {
                let x = 2;
                while (x*x <= p) {
                    if (p%x == 0)
                        return 0
                    x = x + 1
                    }
                return 1
                }

            v.sum(isPrime)
            """, s3, 4, timeout=240
            )

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.fanout")
    def test_fanout_2(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        self.computeUsingSeveralWorkers("""
            let v = Vector.range(20000000)

            let isPrime = fun(p) {
                let x = 2;
                while (x*x <= p) {
                    if (p%x == 0)
                        return 0
                    x = x + 1
                    }
                return 1
                }

            v.sum(isPrime)
            """, s3, 4, timeout=240,memoryLimitMb=100
            )

    def test_map_with_common(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        res = self.computeUsingSeveralWorkers("""
            let v1 = Vector.range(1000000).paged;

            let v2 = Vector.range(30000000)

            v2.sum(fun(i) { v1[(i * 100) % size(v1)] })
            """, s3, 8, timeout=240,memoryLimitMb=100
            )
        self.assertTrue(res.isResult())

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.vector_string_apply")
    def test_vector_string_apply(self):
        #verify that the compiler doesn't crap out during many runs.
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        res = InMemoryCumulusSimulation.computeUsingSeveralWorkers("""
            let v = Vector.range(10000000)

            let v2 = v.apply(String)

            let v3 = v2.apply({_ + "a"})

            v3.sum(size)
            """,
            s3,
            4,
            timeout=120
            )

        self.assertTrue(res is not None)



    def test_page_glomming_basic(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers("""
            [1].paged + [2].paged
            """, s3, 4, timeout=240, returnSimulation = True
            )
        try:
            sprt = simulation.getWorker(0).getSystemwidePageRefcountTracker()

            def activePageCount():
                return len([x for x in sprt.getAllPages() if sprt.machinesWithPageInRam(x)])

            self.assertBecomesTrueEventually(lambda: activePageCount() == 1, 5.0,
                lambda: "Total number of pages should have become 1, not %s.\nView of system:\n\n%s"
                    % (len(sprt.getAllPages()),sprt.getViewOfSystem())
                )

            sprt = None
        finally:
            simulation.teardown()

    def test_page_glomming_multiple(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers("""
            let v = sum(0, 1000, fun(ix) { [sum(0,ix)].paged });

            (v, v.sum())
            """, s3, 4, timeout=240, returnSimulation = True
            )

        try:
            sprt = simulation.getWorker(0).getSystemwidePageRefcountTracker()

            def activePageCount():
                return len([x for x in sprt.getAllPages() if sprt.machinesWithPageInRam(x)])

            self.assertBecomesTrueEventually(lambda: activePageCount() <= 10, 10.0,
                lambda: "Total number of pages should have become 1, not %s.\nView of system:\n\n%s"
                    % (activePageCount(),sprt.getViewOfSystem())
                )

            sprt = None
        finally:
            simulation.teardown()

    def test_page_glomming_common_pages(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers("""
            let v1 = [1].paged + [2].paged;
            let v2 = v1 + [3].paged;

            (v1, v2)
            """, s3, 4, timeout=240, returnSimulation = True
            )

        try:
            sprt = simulation.getWorker(0).getSystemwidePageRefcountTracker()

            def noOrphanedPages():
                return len(sprt.getPagesThatAppearOrphaned()) == 0

            self.assertBecomesTrueEventually(noOrphanedPages, 5.0,
                lambda: "No pages should be orphaned.\nView of system:\n\n%s"
                    % (sprt.getViewOfSystem())
                )

            sprt = None
        finally:
            simulation.teardown()

    def test_invalidURL(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        res = self.computeUsingSeveralWorkers("""datasets.htpp("not a valid url")""", s3, 1)

        self.assertTrue(res.isException())


    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.vector_transpose")
    def test_vector_transpose(self):
        #verify that the compiler doesn't crap out during many runs.
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        _, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers("1+1",
            s3,
            2,
            memoryLimitMb = 500,
            timeout=10,
            returnSimulation = True,
            channelThroughputMBPerSecond = 50.0
            )

        try:
            result = simulation.compute("""
                let arrangedContiguously = fun (vecs) {
                    let res = vecs.sum().paged;

                    let tr = []
                    let low = 0
                    for v in vecs {
                        tr = tr :: res[low,low+size(v)]
                        low = low + size(v)
                        }

                    tr
                    };

                let transpose = fun(vecOfIndexable) {
                    let vecs = arrangedContiguously(vecOfIndexable)

                    let n = size(vecs[0]);

                    [[vecs[jx][ix] for jx in sequence(size(vecs))] for ix in sequence(n)]
                    };

                let vectors = Vector.range(5000, {Vector.range(300)})

                transpose(vectors)
                """,
                timeout = 30.0
                )

            self.assertTrue(result.isResult())

        finally:
            simulation.teardown()

    def disable_createVectorAndReferenceInMultipleComputations(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = self.computeUsingSeveralWorkers(
            "1+1",
            s3,
            2,
            memoryLimitMb = 1000,
            returnSimulation = True,
            useInMemoryCache = False
            )

        try:
            vecComputation = simulation.createComputation(
                """
                let count = 1000 * 1000 * 40

                let fpow = fun(p) {
                    fun(x) {
                        Float32( (x / 1000000000.0) )
                        }
                    };

                Vector.range(10) ~~ fun(p) {
                    Vector.range(count, fpow(p)).paged
                    }
                """
                )

            #we want to verify that all of these computations use the same copy of the
            #bigvec that we create in the 'vecComputation' instance
            predComp = simulation.createComputation("dataframe.DataFrame(vecs[1,])", vecs=vecComputation)
            regComp = simulation.createComputation("dataframe.DataFrame(vecs[,1])", vecs=vecComputation)

            predCompStr = simulation.createComputation("String(pred)", pred=predComp)
            regCompStr = simulation.createComputation("String(reg)", reg=regComp)

            vecSumComp = simulation.createComputation("vecs ~~ {_.sum()}", vecs=vecComputation)


            simulation.submitComputation(predCompStr)
            simulation.submitComputation(regCompStr)
            simulation.submitComputation(vecSumComp)

            r1 = simulation.waitForAnyResult(timeout=60.0)
            r2 = simulation.waitForAnyResult(timeout=60.0)
            r3 = simulation.waitForAnyResult(timeout=60.0)

            #verify that simulation didn't write to disk
            sprt = simulation.getWorker(0).getSystemwidePageRefcountTracker()

            totalGb = sum([x.bytecount for x in sprt.getAllActivePages()]) / 1024.0 / 1024.0 / 1024.0

            logging.critical("%s", sprt.getViewOfSystem())
            self.assertTrue(totalGb < 2.0, totalGb)
        finally:
            simulation.teardown()

    def test_expansionWithVecOfVec(self):
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

            simulation.getGlobalScheduler().setCheckpointStatusInterval(0.0001)

            simulation.submitComputation("Vector.range(20, fun(ix) { Vector.range(100000+ix).paged }).paged")

            simulation.waitForAnyResult()

            simulation.addWorker()

            self.assertTrue(simulation.waitForHandshake())
        finally:
            simulation.teardown()

