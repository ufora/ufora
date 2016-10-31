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
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

class GbmRegressionPerformanceTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    def dataGenerationScript(self, rowCount, columnCount, seed = 22232425):
        return ("""
let generateNormals = fun(count:, seed:) {
    let it = iterator(math.random.Normal(0, 10, seed));
    [pull it for _ in sequence(count)]
    }
let generateData = fun(nSamples, nFeatures, seed:) {
    let featuresDf = dataframe.DataFrame(
        Vector.range(
            nFeatures,
            { generateNormals(count: nSamples, seed: seed + _) }
            )
        );
    let responseDf = dataframe.DataFrame(
        [generateNormals(count: nSamples, seed: seed + nFeatures)]
        );
    (featuresDf, responseDf)
    };

generateData(%s, %s, seed: %s);
            """ % (rowCount, columnCount, seed)
            )

    def regressionScript(self, maxDepth, nBoosts):
        return """
        let builder =
            math.ensemble.gradientBoosting.GradientBoostedRegressorBuilder(
                nBoosts: %s,
                maxDepth: %s
                );

        builder.iterativeFitter(dfPredictors, dfResponse)
        """ % (nBoosts, maxDepth)

    def gbmRegressionFittingTest(self, nRows, nColumns, depth, nThreads, maxBoosts):
        testName = self.getTestName(nRows, nColumns, depth, maxBoosts, nThreads)

        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
                        self.dataGenerationScript(nRows, nColumns),
                        s3,
                        1,
                        timeout = 360,
                        memoryLimitMb = 30 * 1024,
                        threadCount = nThreads,
                        returnSimulation = True,
                        useInMemoryCache = False
                        )
        try:
            self.assertTrue(result.isResult())

            dfPredictors, dfResponse = result.asResult.result

            fitter = simulation.compute(
                self.regressionScript(depth, 1),
                timeout = 360,
                dfResponse = dfResponse,
                dfPredictors = dfPredictors
                ).asResult.result

            t0 = time.time()

            for nBoosts in range(1, maxBoosts):
                testName = self.getTestName(nRows, nColumns, depth, nBoosts, nThreads)

                predictions = simulation.compute(
                    "fitter.predictionsAndPseudoresiduals()",
                    timeout = 360,
                    fitter = fitter
                    ).asResult.result
                totalTimeToReturnResult = time.time() - t0

                PerformanceTestReporter.recordTest(
                    testName + "_predict", totalTimeToReturnResult, None)

                fitter = simulation.compute(
                    "fitter.nextGivenPredictions(predictions)",
                    timeout = 360,
                    fitter = fitter,
                    predictions = predictions
                    ).asResult.result
                totalTimeToReturnResult = time.time() - t0

                PerformanceTestReporter.recordTest(
                    testName, totalTimeToReturnResult, None)

        finally:
            simulation.teardown()

    def getTestName(self, nRows, nColumns, depth, nBoosts, nThreads):
        return "algorithms.gbm.regression.%sRows_%sCol_Depth%s_%sBoosts_%sThreads" % (
            nRows, nColumns, depth, nBoosts, nThreads)

    def test_gbmRegressionFitting(self):
        self.gbmRegressionFittingTest(nRows=1000000, nColumns=90, depth=5,nThreads=1,maxBoosts=5)
        self.gbmRegressionFittingTest(nRows=1000000, nColumns=90, depth=5,nThreads=4,maxBoosts=5)
        self.gbmRegressionFittingTest(nRows=1000000, nColumns=90, depth=5,nThreads=30,maxBoosts=5)
        self.gbmRegressionFittingTest(nRows=4000000, nColumns=90, depth=5,nThreads=30,maxBoosts=5)
        self.gbmRegressionFittingTest(nRows=10000000, nColumns=90, depth=5,nThreads=30,maxBoosts=5)
        self.gbmRegressionFittingTest(nRows=100000, nColumns=90, depth=5,nThreads=4,maxBoosts=5)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

