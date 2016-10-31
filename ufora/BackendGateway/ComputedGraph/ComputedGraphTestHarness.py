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

import ufora.config.Setup as Setup
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedGraph.BackgroundUpdateQueue as BackgroundUpdateQueue


class ComputedGraphTestHarness(object):
    """Helper class for testing computed graph functionality"""
    def __init__(self):
        self.graph = ComputedGraph.ComputedGraph()

    def refreshGraph(self):
        BackgroundUpdateQueue.pullAll()
        self.graph.flush()


    def executeTest(self, testFun):
        """Push 'self.graph' onto the call context and then call 'testFun' with 'self'."""
        with self.graph:
            testFun(self)

    def executeTestNoArg(self, testFun):
        """Push 'self.graph' onto the call context and then call 'testFun' with 'self'."""
        with self.graph:
            testFun()


def UnderHarness(f):
    """Decorator to indicate that a test should run underneath a computed graph test harness."""

    def testFun(self):
        ComputedGraphTestHarness().executeTestNoArg(lambda: f(self))
    testFun.__name__ = f.__name__

    return testFun

