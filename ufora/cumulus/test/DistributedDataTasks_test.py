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
import time
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

callbackScheduler = CallbackScheduler.singletonForTesting()

TIMEOUT=120

class DistributedDataTasksTests(unittest.TestCase):
    @PerformanceTestReporter.PerfTest("python.datatasks.heterogeneous")
    def test_sortHeterogeneous(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let values = []
            let ct = 1000000
            for ix in sequence(ct)
                values = values :: ix :: Float64(ix)

            let sortedVals = cached`(#ExternalIoTask(#DistributedDataOperation(#Sort(values.paged))))

            let sortedAndHomogenous = fun(v) {
                for ix in sequence(size(v)-1)
                    if (v[ix] >= v[ix+1] or `TypeJOV(v[ix]) is not `TypeJOV(v[ix+1]))
                        throw (ix, v[ix], v[ix+1])
                return true;
                }

            if (size(sortedVals) != size(values))
                throw "expected " + String(size(values)) + ", not " + String(size(sortedVals))
            sortedAndHomogenous(sortedVals[,ct]) and
                sortedAndHomogenous(sortedVals[ct,])
            """

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            1,
            timeout=TIMEOUT,
            memoryLimitMb=1000
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    def basicTaskPathwayTest(self, sz, machines=1, memory=1000):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = __size__;

            //let values = Vector.range(N,fun(x) { ((x * 503) % N, x) }).paged;
            let values = Vector.range(N).paged;

            let s1 = cached`(#ExternalIoTask(#DistributedDataOperation(#Sort(values))))
            let s2 = sorting.sort(values)

            if (size(s1) != size(s2))
                return 'wrong size: %s != %s'.format(size(s1), size(s2))
            for ix in sequence(size(s1))
                if (s1[ix] != s2[ix])
                    return 'not equal: index=%s. %s != %s'.format(ix, s1[ix], s2[ix])
            return true
            """.replace("__size__", str(sz))

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            machines,
            timeout=TIMEOUT,
            memoryLimitMb=memory
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    def test_basicTaskPathwaySmall(self):
        self.basicTaskPathwayTest(100)

    @PerformanceTestReporter.PerfTest("python.datatasks.singlebox_80mb")
    def test_basicTaskPathwayBig(self):
        self.basicTaskPathwayTest(10000000)

    @PerformanceTestReporter.PerfTest("python.datatasks.multibox_80mb")
    def test_basicTaskPathwayMultibox(self):
        self.basicTaskPathwayTest(10000000, 4, 250)

    def weirdStringSort(self, sz, machines=1, memory=1000):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = __size__;

            let values = Vector.range(N, fun(ix) { " " * ix }).paged;

            let s1 = cached`(#ExternalIoTask(#DistributedDataOperation(#Sort(values))))
            let s2 = sorting.sort(values)

            if (size(s1) != size(s2))
                return 'wrong size: %s != %s'.format(size(s1), size(s2))

            for ix in sequence(size(s1))
                if (s1[ix] != s2[ix])
                    return 'not equal: index=%s. %s != %s'.format(ix, s1[ix], s2[ix])
            return true
            """.replace("__size__", str(sz))

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            machines,
            timeout=TIMEOUT,
            memoryLimitMb=memory
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    @PerformanceTestReporter.PerfTest("python.datatasks.weird_string_sort_1")
    def test_weirdStringSort_1(self):
        self.weirdStringSort(10000, 1, 1000)

    @PerformanceTestReporter.PerfTest("python.datatasks.weird_string_sort_2")
    def test_weirdStringSort_2(self):
        self.weirdStringSort(10000, 4, 250)

    def classSortingTest(self, sz, useClass = True, machines=1, memory=1000):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = __size__;

            let C = if (__use_class__) { class { member x; } } else { Int64 }

            let values = Vector.range(N, C).paged;

            let s1 = cached`(#ExternalIoTask(#DistributedDataOperation(#Sort(values))))

            return size(s1) == N
            """.replace("__size__", str(sz)).replace("__use_class__", '1' if useClass else '0')

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            machines,
            timeout=TIMEOUT,
            memoryLimitMb=memory
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    def test_class_sorting_is_fast(self):
        sz = 10000000

        #burn the calculation in.
        self.classSortingTest(sz, useClass=True)
        self.classSortingTest(sz, useClass=False)

        t0 = time.time()

        with PerformanceTestReporter.RecordAsPerfTest("python.datatasks.sort_class_instances"):
            self.classSortingTest(sz, useClass=True)

        t1 = time.time()

        with PerformanceTestReporter.RecordAsPerfTest("python.datatasks.sort_integers"):
            self.classSortingTest(sz, useClass=False)

        t2 = time.time()

        intTime = t2 - t1
        classTime = t1 - t0

        self.assertTrue(classTime < intTime * 5, "Times (ints) %s and (classes) %s were not very close." % (intTime, classTime))

        print intTime, " to sort ints"
        print classTime, " to sort class instances"

class DISABLED:
    def test_takeLookupSemantics(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        takeText = """
            let directTake = fun(v, i) {
                i ~~ fun
                    ((filters.IsInteger(...) ix1,filters.IsInteger(...) ix2)) {
                        try { [v][ix1][ix2] } catch(...) { nothing }
                        }
                    (ix) { try { v[ix] } catch (...) { nothing } }
                };

            let takeFrom = [1,2,3,4].paged;
            let indices = __indices__.paged;

            let result = cached`(#ExternalIoTask(#DistributedDataOperation(#Take(indices, takeFrom))));
            let targetResult = directTake(takeFrom, indices)

            assertions.assertEqual(size(result), size(targetResult))

            for ix in sequence(size(result))
                if (result[ix] is not targetResult[ix])
                    return "Expected %s to yield %s, but got %s".format(
                        indices[ix],
                        targetResult[ix],
                        result[ix]
                        );

            return true;
            """

        def takeTest(indexExpr):
            result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                takeText.replace("__indices__", indexExpr),
                s3,
                1,
                timeout=TIMEOUT,
                memoryLimitMb=1000
                )

            self.assertTrue(result is not None)
            self.assertTrue(result.isResult(), result)
            self.assertTrue(result.asResult.result.pyval == True, result)

        takeTest("[0,1,2,3]")
        takeTest("[0,-1,2,3]")
        takeTest("[0,1,2,30]")
        takeTest("[(0,0),(0,1),(0,2),(0,3)]")
        takeTest("[(0,0),(0,1),(0,2),(0,30)]")
        takeTest("[(0,0),(0,1),(0,2),(3,0)]")
        takeTest("[(0u8,0u16),(0u32,1u64),(0s32,2s8),(0s16,3s64)]")
        takeTest("[0,-1,(), (0,0), (0,0.0), nothing, (1,0), (0u8,6u16), (-1,2)]")

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_sort_2_boxes")
    def test_multiboxDataTasksSort_1(self):
        self.multiboxDataTasksSort(1000)

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_sort_2_boxes_big")
    def test_multiboxDataTasksSort_2(self):
        self.multiboxDataTasksSort(10000000, memoryLimit=250)

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_sort_8_boxes_big")
    def test_multiboxDataTasksSort_3(self):
        self.multiboxDataTasksSort(20000000, workers=8, memoryLimit=250)

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_sort_1_boxes_big")
    def test_multiboxDataTasksSort_4(self):
        self.multiboxDataTasksSort(20000000, workers=1, memoryLimit=2000)

    def multiboxDataTasksSort(self, ct, workers=2, memoryLimit=100, pageSizeOverrideMB=1):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = __ct__;
            let aPrime = 503

            let toSort = Vector.range(N, { ((_ * _) % aPrime, _) }).paged;

            let result = cached`(#ExternalIoTask(#DistributedDataOperation(#Sort(toSort))))

            sorting.isSorted(result)
            """.replace("__ct__", str(ct))

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            workers,
            timeout=TIMEOUT,
            memoryLimitMb=memoryLimit,
            pageSizeOverride=pageSizeOverrideMB*1024*1024
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_take_2_boxes")
    def test_multiboxDataTasksTake_1(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = 10000000;
            let isPrime = fun(p) {
                let x = 2
                while (x*x <= p) {
                    if (p%x == 0)
                        return 0
                    x = x + 1
                    }
                return x
                }

            let takeFrom = Vector.range(N, isPrime).paged;
            let indices = Vector.range(N,fun(x) { (0, (x * 503) % N ) }).paged;

            cached`(#ExternalIoTask(#DistributedDataOperation(#Take(indices, takeFrom)))) ==
                indices ~~ { takeFrom[_[1]] }
            """

        result = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            2,
            timeout=TIMEOUT,
            memoryLimitMb=1000
            )

        self.assertTrue(result is not None)
        self.assertTrue(result.isResult(), result)
        self.assertTrue(result.asResult.result.pyval == True, result)

    @PerformanceTestReporter.PerfTest("python.datatasks.distributed_take_8_boxes")
    def test_multiboxDataTasksTake_2(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = 10 * 1000000;
            let takeFrom = Vector.range(N)
            let indices = Vector.range(N,fun(x) { (0, (x * 503) % N ) });

            cached`(#ExternalIoTask(#DistributedDataOperation(#Take(indices, takeFrom))))[0]
            """

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            text,
            s3,
            8,
            timeout=TIMEOUT,
            memoryLimitMb=200,
            returnSimulation = True
            )

        logging.info("Simulation completed")

        maxHighWatermark = 0

        try:
            for ix in range(8):
                vdm = simulation.getWorkerVdm(ix)
                vdmm = vdm.getMemoryManager()

                logging.info("Total bytes: %s", vdmm.getTotalBytesMmappedHighWaterMark())
                maxHighWatermark = max(maxHighWatermark, vdmm.getTotalBytesMmappedHighWaterMark())
                vdm = None
                vdmm = None

            self.assertTrue(result is not None)
            self.assertTrue(result.isResult(), result)
            self.assertTrue(isinstance(result.asResult.result.pyval,int), result)
        finally:
            simulation.teardown()

        self.assertTrue(maxHighWatermark < 265 * 1024 * 1024)

    def test_takeFromLargeObjects(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = 100;

            //each string is 1 MB
            let takeFrom = [" " * 100 * 100 * 10 * 10 + " " * ix for ix in sequence(N)].paged;
            let indices = Vector.range(N,fun(x) { x }).paged;

            cached`(#ExternalIoTask(#DistributedDataOperation(#Take(indices, takeFrom))))
            """

        try:
            result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                text,
                s3,
                1,
                timeout=TIMEOUT,
                memoryLimitMb=1000,
                returnSimulation = True,
                pageSizeOverride = 1024 * 1024
                )

            self.assertTrue(result is not None)
            self.assertTrue(result.isResult(), result)

            for page in result.asResult.result.getVectorPageIds(simulation.getWorkerVdm(0)):
                self.assertLess(page.bytecount / 1024.0 / 1024.0, 2.0)
        finally:
            simulation.teardown()

    def test_takeFromLargeObjectsAsymmetric(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let N = 20;

            //every thousandth string is 1 MB. Just take those.
            let takeFrom = [
                if (ix % 1000 == 0)
                    (" " * 100 * 100 * 10 * 10 + " " * (ix / 1000))
                else
                    ""
                for ix in sequence(N * 1000)].paged;

            let indices = Vector.range(N,fun(x) { x * 1000 }).paged;

            let result = cached`(#ExternalIoTask(#DistributedDataOperation(#Take(indices, takeFrom))))

            let targetResult = indices ~~ {takeFrom[_]};

            assertions.assertEqual(size(result), size(targetResult))
            assertions.assertEqual(result, targetResult)

            result
            """

        try:
            result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                text,
                s3,
                1,
                timeout=TIMEOUT,
                memoryLimitMb=1000,
                returnSimulation = True,
                pageSizeOverride = 1024 * 1024
                )

            self.assertTrue(result is not None)
            self.assertTrue(result.isResult(), result)

            for page in result.asResult.result.getVectorPageIds(simulation.getWorkerVdm(0)):
                self.assertLess(page.bytecount / 1024.0 / 1024.0, 5.0)
        finally:
            simulation.teardown()

