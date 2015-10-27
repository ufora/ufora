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

class TextManipulationTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    def setupScript(self, nRows, nColumns):
        return '''
        let generateCsv = fun(nRows, nColumns) {
            sum(0, nRows,
                (let sampleRow =
                    [elt for elt in \",\".join(Vector.range(nColumns, { String(_) }))];
                fun(rowIx) {
                    let tr = sampleRow;
                    if (rowIx < nRows - 1)
                        tr = tr :: 10u8
                    tr
                    })
                )
            }
        let csv = generateCsv(%s, %s);
        let chunks = csv.split({ _ == 10u8 });
        chunks;''' % (nRows, nColumns)

    def splitToRowMajorScript(self):
        return '''
                chunks ~~ {
                    _.split({ _ == 44u8}) ~~ { _.dataAsString }
                    }
                '''

    def test_splitToRowMajor(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        nRows = 1000000
        nColumns = 50

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            self.setupScript(nRows, nColumns),
            s3,
            1,
            timeout = 30,
            memoryLimitMb = 45 * 1024,
            threadCount = 30,
            returnSimulation = True,
            useInMemoryCache = False
            )

        try:
            self.assertTrue(result.isResult())

            setup = result.asResult.result

            t0 = time.time()
            result = simulation.compute(
                self.splitToRowMajorScript(),
                timeout = 360,
                chunks = setup
                )
            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result.isResult())

            PerformanceTestReporter.recordTest(
                "algorithms.text.splitToRowMajor.%srows_%scolumns" % (nRows, nColumns),
                totalTimeToReturnResult, None)

        finally:
            simulation.teardown()

    def test_transposeToColumnMajor(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        nRows = 100000
        nColumns = 50

        result, simulation = InMemoryCumulusSimulation.computeUsingSeveralWorkers(
            self.transposeSetupScript(nRows, nColumns),
            s3, 1, timeout = 300, memoryLimitMb = 45 * 1024, threadCount = 30,
            returnSimulation = True, useInMemoryCache = False)

        try:
            self.assertTrue(result.isResult())

            rowMajor = result.asResult.result

            t0 = time.time()
            result = simulation.compute(
                self.transposeRowMajorToColumnMajorScript(nRows, nColumns),
                timeout = 500,
                rowMajor = rowMajor
                )
            totalTimeToReturnResult = time.time() - t0

            self.assertTrue(result.isResult())

            PerformanceTestReporter.recordTest(
                "algorithms.text.transposeRowMajorToColumnMajor.%srows_%scolumns" % (nRows, nColumns),
                totalTimeToReturnResult, None)

        finally:
            simulation.teardown()

    def transposeRowMajorToColumnMajorScript(self, nRows, nColumns):
        return """Vector.range(
                      %s,
                      fun(colIx) {
                          Vector.range(
                              %s,
                              fun(rowIx) {
                                  rowMajor[rowIx][colIx]
                                  }
                              )
                          }
                      )""" % (nColumns, nRows)

    def transposeSetupScript(self, nRows, nColumns):
        return """
            Vector.range(%s, fun(rowIx) {
                Vector.range(
                    %s,
                    fun(colIx) {
                        String(colIx)
                        }
                    )
                })""" % (nRows, nColumns)


if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])



