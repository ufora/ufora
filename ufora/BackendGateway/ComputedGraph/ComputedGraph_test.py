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
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedGraph.ComputedGraphTestHarness as ComputedGraphTestHarness
import StringIO


class SimpleLocation(ComputedGraph.Location):
    """A very simple computed graph location for testing"""
    value = object
    mutVal = ComputedGraph.Mutable(object, lambda: 0)

    def property1(self):
        return self.value

    def property2(self):
        return self.property1 * 2

    def mutValTimes2(self):
        return self.mutVal * 2

    def mutValTimes4(self):
        return self.mutValTimes2 * 2


class TestComputedGraph(unittest.TestCase):
    def test_graph(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.simpleGraphTest)

    def simpleGraphTest(self, harness):
        location = SimpleLocation(value=10)

        self.assertEqual(location.property1, 10)
        self.assertEqual(location.property2, location.property1 * 2)

        self.assertEqual(location.mutVal * 2, location.mutValTimes2)
        self.assertEqual(location.mutVal * 4, location.mutValTimes4)

        location.mutVal = 100
        self.assertEqual(location.mutVal, 100)
        self.assertEqual(location.mutVal * 2, location.mutValTimes2)
        self.assertEqual(location.mutVal * 4, location.mutValTimes4)

    def test_create(self):
        ComputedGraphTestHarness.ComputedGraphTestHarness().executeTest(self.createTest)

    def createTest(self, harness):
        t0 = time.time()
        ct = 0
        while time.time() - t0 < 1.0:
            for ix in range(100):
                SimpleLocation(value=(1, 2, 3, 4, 5, 6))
            ct += 100

        print "creations: ", ct


def executeTestAsMain():
    stringIO = StringIO.StringIO()
    try:
        testLoader = unittest.TestLoader()

        suite = testLoader.loadTestsFromTestCase(TestComputedGraph)
        runner = unittest.TextTestRunner(verbosity=2, stream=stringIO)
        runner.run(suite)

        print "Test Results: " + str(stringIO.getvalue())
    except:
        print "Exception!"
        import traceback
        traceback.print_exc()

