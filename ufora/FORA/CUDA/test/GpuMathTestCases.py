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

import ufora.test.PerformanceTestReporter as PerformanceTestReporter

class GpuMathTestCases:

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
