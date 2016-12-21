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

import unittest
import ufora.FORA.python.FORA as Fora
import ufora.native.FORA as ForaNative
import pickle
import time

class GpuCodegenTest(unittest.TestCase):
    def test_basic_gpu_code_simulation_with_hints(self):
        f = Fora.extractImplValContainer(Fora.eval("""
                fun(i) { 
                    let ix = 0
                    let result = 0
                    while (ix < i)
                        {
                        result = result + ix
                        ix = ix + 1

                        if (ix % 100 == 0)
                            `LocalityHint(ix / 10)
                        }

                    return result
                    }
                """))

        result, threadPoints = ForaNative.compileAndSimulateNativeCfgForGpu(f, 1000, 100)

        for p in threadPoints:
            print p

        self.assertEqual(result.pyval, sum(xrange(1000)))

        #we should interrupt 10 times and then exit with a value
        self.assertEqual(len(threadPoints), 11)
