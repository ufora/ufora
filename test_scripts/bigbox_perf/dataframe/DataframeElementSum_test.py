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
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

class PageLoopTest(unittest.TestCase):
    def dataGenerationScript(self, mbOfData, colCount):
        rowCount = mbOfData * 1024 * 1024 / 8 / colCount

        return ("""
            let (rowCount, columnCount, seed, randomColumnsToPick) = (__ROW_COUNT__, __COL_COUNT__, 43, 5);
            dataframe.DataFrame(Vector.range(columnCount,
                fun(colIdx)
                    {
                    Vector.range(rowCount, fun(rowIdx) { (rowIdx + colIdx) % 3 })
                    }
            ));
            """
            ).replace("__ROW_COUNT__", str(rowCount)).replace("__COL_COUNT__", str(colCount))

    def dataframeSumTest(self, mbOfData, colCount, threadCount, recordResults = True):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        t0 = time.time()

        randomColumnsToPick = 10
        totalRowsToSum = 1000000

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, colCount),
                        s3,
                        count=1,
                        timeout = 360,
                        memoryLimitMb = 10000,
                        threadCount = threadCount,
                        returnSimulation = True,
                        useInMemoryCache = False,
                        channelThroughputMBPerSecond = None
                        )

        try:
            self.assertTrue(result.isResult())

            data = result.asResult.result
            executionScript = ("""
                let randomRowwiseSumFun = fun (row, randomColumnsToPick, baseSeed){
                    let rng = iterator(math.random.MultiplyWithCarry(baseSeed + row.rowIndex()));
                    let tr = nothing;
                    let ix = 0;
                    let rowSize = size(row)
                    while (ix < randomColumnsToPick) {
                        let nextIx = (pull rng) % rowSize;
                        tr = tr + row[nextIx]
                        ix = ix + 1
                        }
                    tr
                }
                let randomColumnsToPick = __subsetSize__;
                let baseSeed = 5;
                sum(0, __rows_to_sum__, fun(ix) { randomRowwiseSumFun(data[ix % size(data)], randomColumnsToPick, baseSeed) })
                """
                .replace("__subsetSize__",str(randomColumnsToPick))
                .replace("__rows_to_sum__",str(totalRowsToSum * threadCount))
                )


            t0 = time.time()
            result = simulation.compute(
                executionScript,
                timeout=1080,
                data=data
                )
            computeDuration = time.time() - t0

            totalValuesAccessed = totalRowsToSum * randomColumnsToPick * threadCount

            totalValuesPerSecondPerThread = totalValuesAccessed * 2 / computeDuration / threadCount

            secondsToDo10MillionPerThread = 10 * 1000000 / totalValuesPerSecondPerThread

            if recordResults:
                PerformanceTestReporter.recordTest(
                    "python.BigBox.RandomColumnAccess.access10mm_%smb_%scols_%sthreads" % (
                        mbOfData,
                        colCount,
                        threadCount
                        ),
                    secondsToDo10MillionPerThread,
                    None
                    )

            self.assertTrue(result.isResult())

            return computeDuration

        finally:
            dfResponse = None
            dfPredictors = None
            result = None
            simulation.teardown()

    def test_PageLoopTestSimulation(self):
        #burn in the compiler
        self.dataframeSumTest(1000, 1000, 1, recordResults = False)

        computeDurations = []
        for columns in [10, 50, 100, 200, 500, 1000]:
            for threads in [1, 2, 4, 8, 16]:
                computeDurations.append(self.dataframeSumTest(1000, columns, threads))

        #the largest compute duration should be no more than 5x the median
        computeDurations = sorted(computeDurations)
        self.assertTrue(computeDurations[len(computeDurations)/2] * 5 > computeDurations[-1])


if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

