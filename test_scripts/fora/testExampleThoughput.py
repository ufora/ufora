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

import ufora.FORA.python.FORA as FORA
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

class ExampleThroughputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        FORA.initialize()

    def test_some_throughput(self):
        def toTest(n):
            FORA.eval("""let v = [0, 0.0]; let res = 0;
                         for ix in sequence(%s * 100000000) { 
                             res = res + v[0] + v[1];
                             }
                         res""" % n)

        PerformanceTestReporter.testThroughput(
            "fora_lang.LangTestPerf.vector.heterogeneousVectorAccessThroughput_100mm", 
            toTest, 
            maxNToSearch=10,
            timeoutInSec=5.0
            )

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

