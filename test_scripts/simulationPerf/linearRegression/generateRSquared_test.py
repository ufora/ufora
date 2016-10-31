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
import numpy
import os
import ufora.config.Setup as Setup
import ufora.native.FORA as ForaNative
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.PythonTestUtilities as PythonTestUtilities
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.cumulus.distributed.PythonIoTaskService as PythonIoTaskService
import ufora.native.TCMalloc as TCMallocNative
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
from inspect import getsourcefile

callbackScheduler = CallbackScheduler.singletonForTesting()

class RSquaredMetricsTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return PythonTestUtilities.computeUsingSeveralWorkers(*args, **kwds)


    @PerformanceTestReporter.PerfTest("algorithms.RSquaredOnLinReg")
    def test_RSquaredOnLinReg(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        dirname = os.path.dirname(os.path.abspath(getsourcefile(lambda _: None)))

        listOfReturns = numpy.genfromtxt(dirname+"/dataBucket/ReturnsFor120Months.csv", dtype=float).tolist()

        text = """
            let maxRSquared = -1;
            let nMonths = 120;
            let returnsVec = %s;

            let nReturns = size(returnsVec) / nMonths - 1;

            let returnForIndex = fun(indx){
                return returnsVec[nMonths * (indx + 1), nMonths * (indx + 2)]
                };

            let target = math.Matrix(returnsVec[,nMonths]);

            let createMatrix = fun(i0, i1, i2, i3, i4, i5) {
                let v0 = returnForIndex(i0);
                let v1 = returnForIndex(i1);
                let v2 = returnForIndex(i2);
                let v3 = returnForIndex(i3);
                let v4 = returnForIndex(i4);
                let v5 = returnForIndex(i5);

                return math.Matrix(v0+v1+v2+v3+v4+v5, (nMonths, 6), `column)
                };

            let createMatrixFromVec = fun(vec ){
                return createMatrix(vec[0], vec[1], vec[2], vec[3], vec[4], vec[5])
                };

            let generateIndicesVec = fun(unifIterator){
                let tup=();
                while (size(tup) < 6){
                   let moveToNext = false;
                   while (not moveToNext){
                      let z = pull unifIterator;
                      let zInt = math.round(z);
                      if (zInt not in tup){
                          tup = tup + (zInt,);
                          moveToNext = true;
                          }
                      }
                    };
                return tup;
                };

            let fitAndReturnRsquared = fun(vecIndices) {
                let aMatrix = createMatrixFromVec(vecIndices);

                let fit = math.regression.LinearRegression(aMatrix, target);
                return fit.rSquared()
                };

            let runSingleSeed = fun(i) {
                let seed = 123123 + i;
                let unifRng  = math.random.UniformReal(0, nReturns - 1, seed);
                let unifIterator = iterator(unifRng);
                let vv = generateIndicesVec(unifIterator);
                return fitAndReturnRsquared(vv)
                }

            let getRSquaredVec = fun(nRuns) { Vector.range(nRuns, runSingleSeed) };

            let burnInPhase = false;
            let rSquared = if (burnInPhase) {
                // there seems to be no help from using burn-in in tsunami
                // environment as of Sept 2, 2014
                // we leave that functionality for future uses, just in case

                let samples = [20,30,40,50];
                let kSample = 0;
                let outs = [];
                while (kSample<size(samples)) {
                    outs = outs :: getRSquaredVec(samples[kSample]);
                    kSample = kSample + 1;
                    };

                getRSquaredVec(3000);
                }
            else {
                getRSquaredVec(3000);
                };

            maxRSquared = max(rSquared);
            maxRSquared
            """ % str(listOfReturns)

        result = self.computeUsingSeveralWorkers(text, s3, 4, timeout=360)

        self.assertTrue(result.isResult())
        self.assertTrue(result.asResult.result.pyval > 0.0 )

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA])

