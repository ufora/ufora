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
import ufora.core.JsonPickle as JsonPickle


class LocationA(ComputedGraph.Location):
    """A very simple computed graph location for testing"""
    value = object

class LocationB(ComputedGraph.Location):
    """A very simple computed graph location for testing"""
    value = object
    value2 = object

JsonPickle.addOverride(LocationB, "__LocB__")


class TestJsonPickler(unittest.TestCase):
    @ComputedGraphTestHarness.UnderHarness
    def test_cgPickling_basic(self):
        loc1 = LocationA(value = 10)
        self.assertPicklable(loc1)

        loc2 = LocationA(value = (1,2,3))
        self.assertPicklable(loc2)

        loc3 = LocationA(value = ({1:2},"2",3, 4.0, None, 5L))

        self.assertPicklable(loc3)

        loc4 = LocationB(value=loc1, value2=loc2)
        self.assertPicklable(loc4)

        loc4 = LocationB(value=loc4, value2=loc4)
        self.assertPicklable(loc4)

        #verify that the override worked
        self.assertTrue("__LocB__" in repr(JsonPickle.toSimple(loc4)))

    def assertPicklable(self, something):
        simple = JsonPickle.toJson(something)
        something2 = JsonPickle.fromJson(simple)

        self.assertIdentical(something, something2)

    def assertIdentical(self, a,b):
        self.assertTrue(a is b, "%s and %s are not identical" % (a,b))

