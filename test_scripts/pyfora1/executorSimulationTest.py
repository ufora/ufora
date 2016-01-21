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
import pyfora
#import ufora.config.Setup as Setup
import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases
import ufora.FORA.python.PurePython.ExecutorTestCommon as ExecutorTestCommon


#import ufora.test.ClusterSimulation as ClusterSimulation


class ExecutorSimulationTest(
        unittest.TestCase,
        ExecutorTestCommon.ExecutorTestCommon,
        ExecutorTestCases.ExecutorTestCases):
    #@classmethod
    #def setUpClass(cls):
        #cls.config = Setup.config()
        #cls.executor = None
        #cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        #cls.simulation.startService()
        #cls.simulation.getDesirePublisher().desireNumberOfWorkers(1)

    #@classmethod
    #def tearDownClass(cls):
        #cls.simulation.stopService()

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return pyfora.connect('http://ufora:30000')

        if cls.executor is None:
            cls.executor = pyfora.connect('http://ufora:30000')
            cls.executor.stayOpenOnExit = True
        return cls.executor


if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline()

