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

import math
import numpy


class MathTestCases(object):
    def test_pure_python_math_module(self):
        vals = [1, -.5, 1.5, 0, 0.0, -2, -2.2, .2]

        # not being tested: math.asinh, math.atanh, math.lgamma, math.erfc, math.acos
        def f():
            functions = [
                math.sqrt, math.cos, math.sin, math.tan, math.asin, math.atan, 
                math.acosh, math.cosh, math.sinh, math.tanh, math.ceil, 
                math.erf, math.exp, math.expm1, math.factorial, math.floor,
                math.log, math.log10, math.log1p
            ]
            tr = []
            for idx1 in range(len(vals)):
                v1 = vals[idx1]
                for funIdx in range(len(functions)):
                    function = functions[funIdx]
                    try:
                        tr = tr + [function(v1)]
                    except ValueError as ex:
                        pass

            return tr

        r1 = self.evaluateWithExecutor(f)
        r2 = f()
        self.assertGreater(len(r1), 100)
        self.assertTrue(numpy.allclose(r1, r2, 1e-6))



