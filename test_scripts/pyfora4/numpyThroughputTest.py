#   Copyright 2015-2016 Ufora Inc.
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

import ufora.config.Setup as Setup
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.test.ClusterSimulation as ClusterSimulation

import pyfora
import numpy as np


class NumpyThroughputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Setup.config()
        cls.executor = None
        cls.simulation = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulation.startService()
        cls.simulation.getDesirePublisher().desireNumberOfWorkers(1)

    @classmethod
    def tearDownClass(cls):
        cls.simulation.stopService()

    def setUp(self):
        self.ufora = pyfora.connect('http://localhost:30000')

    def tearDown(self):
        self.ufora.close()


    def test_connection(self):
        self.assertIsNotNone(self.ufora)


    def test_matrix_dot_product(self):
        dimension = 1000.0
        with self.ufora.remotely:
            a = np.arange(dimension**2).reshape((dimension, dimension))
            b = np.arange(0.0, 10000.0, 10000.0/(dimension**2)).reshape((dimension, dimension))

        def f(n):
            with self.ufora.remotely:
                for _ in xrange(n):
                    np.dot(a, b)

        PerformanceTestReporter.testThroughput(
            "pyfora.numpy.matrix_dot_product_1000x1000",
            f,
            maxNToSearch=10,
            timeoutInSec=30.0
            )

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])
