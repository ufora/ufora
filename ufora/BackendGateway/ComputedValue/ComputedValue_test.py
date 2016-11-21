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
import logging
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.BackendGateway.ComputedValue.ComputedValueTestCases as ComputedValueTestCases
import ufora.cumulus.distributed.CumulusGatewayInProcess as CumulusGatewayInProcess
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()
callbackSchedulerFactory = callbackScheduler.getFactory()

#class TestComputedValue(unittest.TestCase, ComputedValueTestCases.ComputedValueTestCases):
    #def setUp(self):
        #self.graph = None
        #self.computedValueGateway = None
        #setUpComputedValueTest(self)

    #def tearDown(self):
        #tearDownComputedValueTest(self)

#def setUpComputedValueTest(tester):
    #tester.graph = ComputedGraph.ComputedGraph()
    #tester.graph.__enter__()

    #def gatewayFactory(callbackScheduler, vdm):
        #return CumulusGatewayInProcess.InProcessGateway(callbackSchedulerFactory, callbackScheduler, vdm)

    #tester.computedValueGateway = \
            #ComputedValueGateway.CumulusComputedValueGateway(
                #callbackSchedulerFactory,
                #callbackScheduler,
                #gatewayFactory
                #)
    #tester.computedValueGateway.__enter__()

#def tearDownComputedValueTest(tester):
    #logging.info("Tearing down test harness")
    #tester.computedValueGateway.__exit__(None, None, None)
    #tester.graph.__exit__(None, None, None)
    #tester.computedValueGateway.teardown()
    #tester.computedValueGateway = None
    #tester.graph = None
    #logging.info("Test harness torn down.")

