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
import numpy
import os
import logging
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

class GenerateGaussiansTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return PythonTestUtilities.computeUsingSeveralWorkers(*args, **kwds)


    @PerformanceTestReporter.PerfTest("algorithms.GenerateGaussians")
    def test_GenerateGaussians(self):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        # Settings: 500 nBatches == 1.5GB    of memory allocation
        nBatches = 50
        memInGB = nBatches * 100000 * 4 * 8 / (1024.0**3)

        text = """
                let generateWithSingleSeed = fun(i, mu, sigma){
                    let nSamplesToGenerate = 100000;
                    let seed = 123123 + i;
                    let stdNormal = math.random.Normal(mu, sigma, seed);
                        return iter.toVector(iter.subseq(stdNormal, 0, nSamplesToGenerate));
                };
                let mu=0;
                let sigma=0.1;
                let vecOfVecs = Vector.range( 3* %i, fun(i){generateWithSingleSeed(i, mu, sigma)} );
                let longVec = sum(vecOfVecs);
                let subvecSize = size(longVec) / 3;
                let NX = subvecSize;
                let NY = 3;
                let columns = [ longVec[i*NX,(i+1)*NX] for i in sequence(NY) ];
                let dfPredictors = dataframe.DataFrame(columns);
                let c = 1.0/3.0;
                let target = Vector.range( subvecSize, fun(i){ c*columns[0][i] + c*columns[1][i] + c*columns[2][i] } );
                let dfResponse = dataframe.DataFrame([target]);

                size(dfPredictors) == size(dfResponse);
            """ % nBatches

        result = self.computeUsingSeveralWorkers(text, s3, 4, timeout=360, memoryLimitMb=1000)

        self.assertTrue(result.isResult())
        self.assertTrue(result.asResult.result.pyval)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA])

