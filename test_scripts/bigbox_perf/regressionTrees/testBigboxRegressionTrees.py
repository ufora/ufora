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

class RegressionTreesPerformanceTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)


    def dataGenerationScript(self, mbOfData, columns):
        valueCount = mbOfData * 1024 * 1024 / 8
        rowCount = valueCount / columns

        return ("""
            let data = Vector.range(__columns__) ~~ fun(c) {
                Vector.range(__rows__, fun(r) { Float64(r % (c+2)) })
                };

            let dfResponse = dataframe.DataFrame(data[-1,], columnNames:["response"]);
            let dfPredictors = dataframe.DataFrame(data[,-1]);

            (dfResponse, dfPredictors)
            """ .replace("__columns__", str(columns))
                .replace("__rows__", str(rowCount))
            )

    def regressionScript(self, treeDepth, minSamplesSplit):
        return """
        let regressionTreeBuilder =
            math.tree.RegressionTree.RegressionTreeBuilder(
                maxDepth:%s, minSamplesSplit:%s
                );

        let fitRegressionTree =
            regressionTreeBuilder.fit(dfPredictors, dfResponse);

        fitRegressionTree
        """ % (treeDepth, minSamplesSplit)

    def regressionTreePredictionTest(self, mbOfData, columns, testName,
                                     treeDepth, threads, minSamplesSplit=50):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, columns),
                        s3,
                        1,
                        timeout = 360,
                        memoryLimitMb = 45 * 1024,
                        threadCount = threads,
                        returnSimulation = True,
                        useInMemoryCache = False
                        )
        try:
            self.assertTrue(result.isResult())

            dfResponse, dfPredictors = result.asResult.result

            fitTree = simulation.compute(
                self.regressionScript(treeDepth, minSamplesSplit - 1),
                timeout=120,
                dfResponse=dfResponse,
                dfPredictors=dfPredictors
                )

            def predictionScript(dirtyFlag=1):
                return ";(%s; fitRegressionTree.predict(dfPredictors));" % dirtyFlag

            t0 = time.time()
            result = simulation.compute(
                predictionScript(),
                timeout=120,
                dfPredictors=dfPredictors,
                fitRegressionTree=fitTree.asResult.result
                )
            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result.isResult())

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)

        finally:
            simulation.teardown()

    def regressionTreeFittingTest(self, mbOfData, columns, testName,
                                  treeDepth, threads, minSamplesSplit=50):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(mbOfData, columns),
                        s3,
                        1,
                        timeout = 360,
                        memoryLimitMb = 45 * 1024,
                        threadCount = threads,
                        returnSimulation = True,
                        useInMemoryCache = False
                        )
        try:
            self.assertTrue(result.isResult())

            dfResponse, dfPredictors = result.asResult.result

            # allow a burn-in run
            simulation.compute(
                self.regressionScript(treeDepth, minSamplesSplit - 1),
                timeout=120,
                dfResponse=dfResponse,
                dfPredictors=dfPredictors
                )

            t0 = time.time()
            result = simulation.compute(
                self.regressionScript(treeDepth, minSamplesSplit),
                timeout = 120,
                dfResponse=dfResponse,
                dfPredictors=dfPredictors
                )
            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result.isResult())

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)

        finally:
            simulation.teardown()

    def test_regressionTreeFitting(self):
        for mb in [1000]:
            for cols in [90]:
                for depth in [3, 5, 7, 9]:
                    for threads in [32]:
                        testName="algorithms.RegressionTreeFitting.%sMB_%scol_depth%s_%sthreads" % (
                            mb, cols, depth, threads)

                        self.regressionTreeFittingTest(
                            mbOfData=mb,
                            columns=cols,
                            testName=testName,
                            treeDepth=depth,
                            threads=threads
                            )

    def test_regressionTreePrediction(self):
        for mb in [1000]:
            for cols in [90]:
                for depth in [3, 5, 7, 9]:
                    for threads in [32]:
                        testName="algorithms.RegressionTreePrediction.%sMB_%scol_depth%s_%sThreads" % (
                            mb, cols, depth, threads)
                        self.regressionTreePredictionTest(
                            mbOfData=mb,
                            columns=cols,
                            testName=testName,
                            treeDepth=depth,
                            threads = threads
                            )

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

