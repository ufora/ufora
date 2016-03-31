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
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

class LargeDatasetBigLMTest(unittest.TestCase):
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

    def largeDatasetBigLMTest(self, mbOfData, columns, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        t0 = time.time()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, columns),
                        s3,
                        1,
                        timeout = 360,
                        memoryLimitMb = 50 * 1024,
                        threadCount = threads,
                        returnSimulation = True,
                        useInMemoryCache = False
                        )

        if testName is not None:
            PerformanceTestReporter.recordTest(testName + "_create", time.time() - t0, None)

        try:
            self.assertTrue(result.isResult())

            dfResponse, dfPredictors = result.asResult.result

            regressionScript = """
                let model = math.regression.LinearRegression(dfPredictors, dfResponse, fitIntercept: false);
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

            self.assertTrue(result.isResult())

            if testName is not None:
                PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            dfResponse = None
            dfPredictors = None
            result = None
            simulation.teardown()

    def test_LargeDatasetBigLM(self):
        for mb in [10, 100, 1000, 2000, 4000, 8000, 16000, 32000]:
            for cols in [2, 10, 50]:
                #a single thread can do a few (e.g. 6) gb/sec of dotproduct on my box
                totalExpectedComputeSeconds = mb * cols * cols / 2 / 6
                if totalExpectedComputeSeconds > 100:
                    threadOptions = [32]
                else:
                    threadOptions = [4, 32]

                for threads in threadOptions:
                    self.largeDatasetBigLMTest(mb, cols, threads, "algorithms.linearRegression.%sMB_%sCol_%sThreads" % (mb, cols, threads))

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

