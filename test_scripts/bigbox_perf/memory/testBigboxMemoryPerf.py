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
import threading
import ufora.native.FORA as ForaNative
import ufora.FORA.python.FORA as FORA
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()


class BigboxMemoryPerformanceTest(unittest.TestCase):
    measurementTime = 1.0
    coreList = [1,4,32]
    allocSizeList = [1,2,4,8,16]

    def testMemoryAllocation(self):
        measurementTime = self.measurementTime
        for cores in self.coreList:
            for allocSize in self.allocSizeList:
                PerformanceTestReporter.recordTest(
                    "python.BigBox.MemoryPoolAlloc.SecondsPerGB.%sCore_%sMB" % (cores, allocSize),
                    self.measureMemoryAllocationPerformance(measurementTime, 1024 * 1024 * allocSize, cores),
                    None
                    )

    def testMmapAllocationAndInitialize(self):
        measurementTime = self.measurementTime
        for cores in self.coreList:
            for allocSize in self.allocSizeList:
                PerformanceTestReporter.recordTest(
                    "python.BigBox.MmapAllocAndInit.SecondsPerGB.%sCore_%sMB" % (cores, allocSize),
                    self.measureMmapPerformance(measurementTime, 1024 * 1024 * allocSize, cores, True),
                    None
                    )

    def testMmapAllocation(self):
        measurementTime = self.measurementTime
        for cores in self.coreList:
            for allocSize in self.allocSizeList:
                PerformanceTestReporter.recordTest(
                    "python.BigBox.MmapAlloc.SecondsPerGB.%sCore_%sMB" % (cores, allocSize),
                    self.measureMmapPerformance(measurementTime, 1024 * 1024 * allocSize, cores, False),
                    None
                    )

    def testMemoryUpdate(self):
        measurementTime = self.measurementTime
        for cores in self.coreList:
            for allocSize in self.allocSizeList:
                PerformanceTestReporter.recordTest(
                    "python.BigBox.MemoryUpdate.SecondsPerGB.%sCore_%sMB" % (cores, allocSize),
                    self.measureMemoryUpdatePerformance(measurementTime, 1024 * 1024 * allocSize, cores),
                    None
                    )


    def measureMemoryAllocationPerformance(self, measurementTime, blockSize, threadCount):
        t0 = time.time()

        results = []

        vdmm = ForaNative.createTestingVDMM()

        def runTest():
            results.append(
                ForaNative.executeBigVectorHandleAllocationsForTimePeriod(
                        vdmm,
                        measurementTime,
                        blockSize
                        )
                )

        threads = [threading.Thread(target=runTest) for ix in range(threadCount)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return (time.time() - t0) / (sum(results) / 1024.0 ** 3)

    def measureMemoryUpdatePerformance(self, measurementTime, blockSize, threadCount):
        t0 = time.time()

        results = []

        def runTest():
            results.append(
                ForaNative.executeMemoryUpdatesForTimePeriod(
                        measurementTime,
                        blockSize
                        )
                )

        threads = [threading.Thread(target=runTest) for ix in range(threadCount)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return (time.time() - t0) / (sum(results) / 1024.0 ** 3)

    def measureMmapPerformance(self, measurementTime, blockSize, threadCount, initializeData):
        t0 = time.time()

        results = []

        vdmm = ForaNative.createTestingVDMM()

        def runTest():
            results.append(
                ForaNative.executeMMapAndFreeForTimePeriod(
                        vdmm,
                        measurementTime,
                        blockSize,
                        initializeData
                        )
                )

        threads = [threading.Thread(target=runTest) for ix in range(threadCount)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        return (time.time() - t0) / (sum(results) / 1024.0 ** 3)

    def test_verifySmallAllocNotRemapping(self):
        vdmm = ForaNative.createTestingVDMM()

        ForaNative.executeBigVectorHandleAllocationsForTimePeriod(
            vdmm,
            .25,
            1024 * 1024
            )

        bytes1 = vdmm.totalBytesMmappedCumulatively()

        ForaNative.executeBigVectorHandleAllocationsForTimePeriod(
            vdmm,
            1.0,
            1024 * 1024
            )

        bytes2 = vdmm.totalBytesMmappedCumulatively()

        self.assertTrue(bytes2 <= 1024 * 1024 * 4)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

