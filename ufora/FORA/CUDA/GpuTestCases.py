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
import pickle
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import math

class GpuTestCases:
    def compareCudaToCPU(self, funcExpr, vecExpr):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = """
            let f = __funcExpr__;
            let i = __vecExpr__;
            let cuda = `CUDAVectorApply(f, [i])[0];
            let cpu = f(i)

            if (cuda == cpu)
                true
            else
                throw String(cuda) + " != " + String(cpu)
            """.replace("__funcExpr__", funcExpr).replace("__vecExpr__", vecExpr)

        res = InMemoryCumulusSimulation.computeUsingSeveralWorkers(text, s3, 1, timeout=120, threadCount=4)
        self.assertIsNotNone(res)
        self.assertTrue(res.isResult(), "Failed with %s on %s: %s" % (funcExpr, vecExpr, res))


    def test_cuda_read_tuples(self):
        self.compareCudaToCPU("fun((a,b)) { (b,a) }", "(1,2)")
        self.compareCudaToCPU("fun((a,b)) { b + a }", "(1,2)")
        self.compareCudaToCPU("fun((a,b)) { b + a }", "(1s32,2s32)")
        self.compareCudaToCPU("fun(b) { b + 1s32 }", "2")

        self.compareCudaToCPU("math.log", "2")


    def test_cuda_tuple_alignment(self):
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "(1s32,2,2s32)")
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "(1u32,2,2s32)")
        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "(1u16,2s32,2)")

        self.compareCudaToCPU("fun((a,b,c)) { a+b+c }", "(10.0f32, 2.0, 2)")
        self.compareCudaToCPU(
                "fun((a,b,c,d,e,f)) { a+b+c+d+e+f }",
                "(2u16, 3s32, 4s64, 5.0f16, 6.0f32, 7.0f64)"
                )


    def test_cuda_conversions(self):
        s_integers = ["2s16", "3s32", "4s64", "5"]
        u_integers = ["2u16", "3u32", "4u64", "5"]
        floats = ["2.2f32", "3.3f64", "4.4"]

        numbers = s_integers + u_integers + floats
        for n1 in numbers:
            for n2 in numbers:
                for op in ["+", "-", "*" ]:    # TODO: add division, currently broken
                    self.compareCudaToCPU(
                            "fun((a,b)) { a " + op + " b }",
                            "(" + n1 + ", " + n2 + ")"
                            )


    def check_precision_of_function_on_GPU(self, function, input):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()
        text = """
            let f = fun(x) {
                `""" + function + """(x)
                }
            `CUDAVectorApply(f, [""" + str(input) + """])[0]
            """
        res = InMemoryCumulusSimulation.computeUsingSeveralWorkers(text, s3, 1, timeout=120, threadCount=4)
        self.assertIsNotNone(res)
        self.assertTrue(res.isResult(), res)
        gpuValue = res.asResult.result.pyval
        methodToCall = getattr(math, function)
        pythonValue = methodToCall(input)
        self.assertTrue(abs(gpuValue - pythonValue) < 1e-10)

    def test_precision_of_exp(self):
        for x in xrange(-10000, 10000, 10000):
            print x
            self.check_precision_of_function_on_GPU("exp", x)

    def test_precision_of_log(self):
        for x in [0.001, 0.01, 0.1, 0.5, 0.8, 0.9, 0.99, 0.9999, 1.0, 1.0001, 1.01, 1.1, 10, 1000, 1000000, 1000000000]:
            self.check_precision_of_function_on_GPU("log", x)

    def test_precision_of_cos(self):
        for x in xrange(0, 360, 20):
            self.check_precision_of_function_on_GPU("cos", x)

    def test_precision_of_sin(self):
        for x in xrange(0, 360, 20):
            self.check_precision_of_function_on_GPU("sin", x)


    def basic_gpu_works_helper(self, function, onGPU=True):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        testingVectorText = "Vector.range(1024*4, {_+1000000})"

        text = """
            let f = fun(ct) {
                let res = 0.0
                let x = 1.0
                while (x < ct)
                    {
                    x = x + 1.0
                    res = res + `""" + function + """(x)
                    }
                res
                }"""

        if onGPU:
            text += """`CUDAVectorApply(f,""" + testingVectorText + """)"""
        else:
            text += testingVectorText + """ ~~ f"""

        res = InMemoryCumulusSimulation.computeUsingSeveralWorkers(text, s3, 1, timeout=120, threadCount=4)
        self.assertIsNotNone(res)
        self.assertTrue(res.isResult(), res)

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
