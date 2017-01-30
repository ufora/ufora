#   Copyright 2016 Ufora Inc.
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

import numpy
import time
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

class GpuPerformanceTestCases:

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfExpsUsingGPU")
    def test_basic_gpu_works_exp1(self):
        self.basic_gpu_works_helper("exp", onGPU=True)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfExpsWithoutGPU")
    def test_basic_gpu_works_exp2(self):
        self.basic_gpu_works_helper("exp", onGPU=False)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfLogsUsingGPU")
    def test_basic_gpu_works_log1(self):
        self.basic_gpu_works_helper("log", onGPU=True)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfLogsWithoutGPU")
    def test_basic_gpu_works_log2(self):
        self.basic_gpu_works_helper("log", onGPU=False)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfCosinesUsingGPU")
    def test_basic_gpu_works_cos1(self):
        self.basic_gpu_works_helper("cos", onGPU=True)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfCosinesWithoutGPU")
    def test_basic_gpu_works_cos2(self):
        self.basic_gpu_works_helper("cos", onGPU=False)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfSinesUsingGPU")
    def test_basic_gpu_works_sin1(self):
        self.basic_gpu_works_helper("sin", onGPU=True)

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.LotsOfSinesWithoutGPU")
    def test_basic_gpu_works_sin2(self):
        self.basic_gpu_works_helper("sin", onGPU=False)

    MATMULT_SIZE = 3000
    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.MatMultOnGPU")
    def test_matmult_gpu(self):
        dimSize = self.MATMULT_SIZE
        captureExpr = '''
                let mat_d = __size__;
                let mat1 = Vector.range(mat_d, fun(x){Vector.range(mat_d, fun(y){(x*mat_d + y) * 1.0})});
                let mat2 = Vector.range(mat_d, fun(x){Vector.range(mat_d, fun(y){(y*mat_d + x) * 1.0})});
                '''.replace('__size__', str(dimSize))
        functionExpr = '''
                fun((x,y)) {
                  let sum = 0;
                  for k in sequence(mat_d) {
                    sum = mat1[x][k] * mat2[k][y]
                  }
                  sum
                }'''

        vectorExpr = '[(x,y) for y in sequence(mat_d) for x in sequence(mat_d)]'

        print "CapEx: ", captureExpr
        print "FunEx: ", functionExpr
        print "VecEx: ", vectorExpr

        t0 = time.time()
        self.runOnGPU(functionExpr, vectorExpr, captureExpr)
        print "GPU took ", time.time() - t0, " to do mm ", dimSize

    @PerformanceTestReporter.PerfTest("python.InMemoryCumulus.GPU.MatMultWithNumpy")
    def test_matmult_numpy(self):
        dimSize = self.MATMULT_SIZE
        m1 = numpy.ones((dimSize,dimSize))
        m2 = numpy.ones((dimSize,dimSize))

        t0 = time.time()
        numpy.matmul(m1,m2)
        print "Numpy took ", time.time() - t0, " to do mm ",dimSize, " in one CPU"

