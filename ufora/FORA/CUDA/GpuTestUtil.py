#   Copyright 2015,2016 Ufora Inc.
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

import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import math

class GpuTestUtil:
    def compareCudaToCPUnoCheck(self, funcExpr, vecExpr, captureExpr=""):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        text = captureExpr + """
            let f = __funcExpr__;
            let vec = __vecExpr__;
            let cuda = `CUDAVectorApply(f, vec);
            let cpu = [f(x) for x in vec]

            if (cuda == cpu)
                true
            else
                throw String(cuda) + " != " + String(cpu)
            """.replace("__funcExpr__", funcExpr).replace("__vecExpr__", vecExpr)

        res = InMemoryCumulusSimulation.computeUsingSeveralWorkers(text, s3, 1, timeout=120, threadCount=4)
        self.assertIsNotNone(res)
        return res

    def compareCudaToCPU(self, funcExpr, vecExpr, captureExpr=""):
        res = self.compareCudaToCPUnoCheck(funcExpr, vecExpr, captureExpr)
        self.assertTrue(res.isResult(), "Failed with %s on %s: %s" % (funcExpr, vecExpr, res))

    def checkCudaRaises(self, funcExpr, vecExpr, captureExpr=""):
        res = self.compareCudaToCPUnoCheck(funcExpr, vecExpr, captureExpr)
        self.assertTrue(res.isException(), "Expected exception with %s on %s: %s" % (funcExpr, vecExpr, res))

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

