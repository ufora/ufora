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
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

callbackScheduler = CallbackScheduler.singletonForTesting()

class MultimachineJoinSimulationTest(unittest.TestCase):
    def dataGenerationScript(self, mbOfData, columns):
        valueCount = mbOfData * 1000 * 1000 / 8
        rowCount = valueCount / columns

        return ("""
            let data = Vector.range(__columns__) ~~ fun(c) {
                Vector.range(__rows__, fun(r) { Float64(r * __columns__ + c) })
                };

            data
            """ .replace("__columns__", str(columns))
                .replace("__rows__", str(rowCount))
            )

    def largeDatasetJoinTest(self, mbOfData, columns, threads, machineCount, ratio = .5):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        t0 = time.time()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, columns),
                        s3,
                        machineCount,
                        timeout = 360,
                        memoryLimitMb = mbOfData / ratio / machineCount,
                        #channelThroughputMBPerSecond = 100.0,
                        threadCount = threads,
                        returnSimulation = True,
                        useInMemoryCache = False,
                        disableEventHandler = True
                        )

        try:
            self.assertTrue(result.isResult())

            data = result.asResult.result

            joinScript = """
                    let leftDF = dataframe.DataFrame(data[,size(data)/2])
                    let rightDF = dataframe.DataFrame(data[size(data)/2,])

                    size(leftDF.join(rightDF, on: "C0", how: `outer, chunkSize: 1000000, areSorted:true))
                    """

            t0 = time.time()
            result = simulation.compute(
                joinScript,
                timeout=1080,
                data=data
                )
            totalTimeToReturnResult = time.time() - t0

            logging.info("Total time to join: %s", totalTimeToReturnResult)

            self.assertTrue(result.isResult(), result)

            PerformanceTestReporter.recordTest(
                "algorithms.Join.inMemory_%sMB_%scols_%sthreads_%smachines" %
                    (mbOfData, columns,threads,machineCount),
                totalTimeToReturnResult,
                None
                )
        finally:
            dfResponse = None
            dfPredictors = None
            result = None
            simulation.teardown()

    def test_MultiboxJoin(self):
        self.largeDatasetJoinTest(400, 6, 1, 6, ratio=.2)

    def test_MultiboxJoin_2(self):
        self.largeDatasetJoinTest(400, 10, 1, 6, ratio=.2)

    def test_MultiboxJoin_singlebox(self):
        self.largeDatasetJoinTest(400, 6, 4, 1, ratio=.2)

    def test_MultiboxJoin_singlebox_2(self):
        self.largeDatasetJoinTest(400, 6, 4, 1, ratio=.2)

