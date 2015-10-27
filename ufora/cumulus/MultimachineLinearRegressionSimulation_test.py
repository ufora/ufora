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
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

callbackScheduler = CallbackScheduler.singletonForTesting()

class MultimachineLinearRegressionSimulationTest(unittest.TestCase):
    def dataGenerationScript(self, mbOfData, columns):
        valueCount = mbOfData * 1024 * 1024 / 8
        rowCount = valueCount / columns

        return ("""
            let data = Vector.range(__columns__) ~~ fun(c) {
                Vector.range(__rows__, fun(r) { if (c == 0) 1.0 else Float64(r % (c+2)) })
                };

            let dfResponse = dataframe.DataFrame(data[-1,]);
            let dfPredictors = dataframe.DataFrame(data[,-1]);

            (dfResponse, dfPredictors)
            """ .replace("__columns__", str(columns))
                .replace("__rows__", str(rowCount))
            )

    def largeDatasetBigLMTest(self, mbOfData, columns, threads, machineCount, ratio = .5):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        t0 = time.time()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, columns),
                        s3,
                        machineCount,
                        timeout = 360,
                        memoryLimitMb = mbOfData / ratio / machineCount,
                        channelThroughputMBPerSecond = 100.0,
                        threadCount = threads,
                        returnSimulation = True,
                        useInMemoryCache = False
                        )

        try:
            self.assertTrue(result.isResult())

            dfResponse, dfPredictors = result.asResult.result

            regressionScript = """
                    let model = math.regression.LinearRegression(dfPredictors, dfResponse,coefficientsOnly:true);
                    let coefficients = model.coefficients();
                    coefficients[0]
                    """

            t0 = time.time()
            result = simulation.compute(
                regressionScript,
                timeout=1080,
                dfResponse=dfResponse,
                dfPredictors=dfPredictors
                )
            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result.isResult(), result)

            self.assertTrue(result.isResult())

            print "Done with the first regression"

            regressionScript2 = """
                    let newCol = dfPredictors.rowApply(fun(row) { math.sin(row[0] ) })
                    let newCol2 = dfPredictors.rowApply(fun(row) { math.sin(row[0] + 1) })
                    let model2 = math.regression.LinearRegression(dfPredictors.addColumn(newCol).addColumn(newCol2), dfResponse, coefficientsOnly:true)
                    model2.coefficients()[0]
                    """

            result2 = simulation.compute(
                regressionScript2,
                timeout=1080,
                dfResponse=dfResponse,
                dfPredictors=dfPredictors
                )

            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result2.isResult(), result2)

            PerformanceTestReporter.recordTest(
                "algorithms.linearRegression.inMemory_%sMB_%scols_%sthreads_%smachines" %
                    (mbOfData, columns,threads,machineCount),
                totalTimeToReturnResult,
                None
                )
        finally:
            dfResponse = None
            dfPredictors = None
            result = None
            simulation.teardown()

    def test_MultiboxLinearRegression(self):
        self.largeDatasetBigLMTest(1000, 30, 1, 4)

