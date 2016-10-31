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
        cls.ufora = pyfora.connect('http://localhost:30000')

    @classmethod
    def tearDownClass(cls):
        cls.ufora.close()
        cls.simulation.stopService()


    def test_array_subtraction_large(self):
        def subtract(a, b):
            return a - b

        self.array_binary_operation(1000000.0, subtract, "vector_subtract")


    def test_array_subtraction_small(self):
        def subtract(a, b):
            return a - b

        self.array_binary_operation(1000.0, subtract, "vector_subtract")


    def test_array_addition_large(self):
        def add(a, b):
            return a + b

        self.array_binary_operation(1000000.0, add, "vector_add")


    def test_array_addition_small(self):
        def add(a, b):
            return a + b

        self.array_binary_operation(1000.0, add, "vector_add")


    def test_array_multiplication_large(self):
        def multiply(a, b):
            return a * b

        self.array_binary_operation(1000000.0, multiply, "vector_multiply")


    def test_array_multiplication_small(self):
        def multiply(a, b):
            return a * b

        self.array_binary_operation(1000.0, multiply, "vector_multiply")


    def array_binary_operation(self, dimension, op, test_name):
        with self.ufora.remotely:
            a = np.arange(dimension)
            b = np.arange(dimension)

        def f(n):
            with self.ufora.remotely:
                for _ in xrange(n):
                    op(a, b)

        PerformanceTestReporter.testThroughput(
            "pyfora.numpy.%s_%d" % (test_name, dimension),
            f,
            maxNToSearch=20,
            timeoutInSec=20.0
            )


    def test_matrix_dot_product_large(self):
        self.matrix_dot_product(1000.0)


    def test_matrix_dot_product_small(self):
        self.matrix_dot_product(100.0)


    def matrix_dot_product(self, dimension):
        with self.ufora.remotely:
            a = np.arange(dimension**2).reshape(
                (int(dimension), int(dimension)))
            b = np.arange(dimension**2).reshape(
                (int(dimension), int(dimension)))

        def f(n):
            with self.ufora.remotely:
                for _ in xrange(n):
                    np.dot(a, b)

        PerformanceTestReporter.testThroughput(
            "pyfora.numpy.matrix_dot_product_%dx%d" % (dimension, dimension),
            f,
            maxNToSearch=20,
            timeoutInSec=20.0
            )


    def test_vector_dot_product_large(self):
        self.vector_dot_product(1000000.0)


    def test_vector_dot_product_small(self):
        self.vector_dot_product(1000.0)


    def vector_dot_product(self, dimension):
        with self.ufora.remotely:
            a = np.arange(dimension)
            b = np.arange(dimension)

        def f(n):
            with self.ufora.remotely:
                for _ in xrange(n):
                    np.dot(a, b)

        PerformanceTestReporter.testThroughput(
            "pyfora.numpy.vector_dot_product_%d" % dimension,
            f,
            maxNToSearch=20,
            timeoutInSec=20.0
            )

if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])
