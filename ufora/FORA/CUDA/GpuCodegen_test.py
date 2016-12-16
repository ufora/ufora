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
    def test_basic_gpu_codegen(self):
        f = Fora.extractImplValContainer(Fora.eval("""let v = [1.0,2.0,3.0,4.0]; 
                fun(i) { 
                    if (i%2 == 0)
                        return (v[i],i)
                    return 3
                    }
                """))

        t0 = time.time()
        print ForaNative.compileAndStringifyNativeCfgForGpu(f)
        print "took ", time.time() - t0
