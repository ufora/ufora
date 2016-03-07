#   Copyright 2016 Ufora Inc.
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


import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory
import ufora.FORA.python.PurePython.ExecutorTestCommon as ExecutorTestCommon
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

from pyfora.algorithms.logistic.BinaryLogisticRegressionFitter import \
    BinaryLogisticRegressionFitter


import time
import unittest
import pandas
import math


def generate_random_x(seed, nSamples, nColumns):
    columns = [
        generate_column(seed + ix, nSamples) for ix in xrange(nColumns)
        ]

    # !!!!!!!!!!! NOTE: in normal pandas, `columns` is defining
    # the *rows* of the dataframe. In pyfora, `columns` defines
    # the *columns* of the dataframe. !!!!!!!!
    return pandas.DataFrame(columns)

def generate_random_y(x, coefficients, seed):
    y = x.dot(coefficients)
    y = [math.exp(elt) for elt in y]
    y = [1.0 / (1.0 + elt) for elt in y]

    probabilities = generate_uniform_column(seed, len(x))

    tr = []
    for ix in xrange(len(x)):
        if probabilities[ix] >= y[ix]:
            tr = tr + [1.0]
        else:
            tr = tr + [0.0]

    return pandas.Series(tr)

def generate_column(seed, nSamples):
    return [2.0 * x - 1.0 for x in generate_uniform_column(seed, nSamples)]

def generate_uniform_column(seed, nSamples):
    m = 4294967296
    a = 1664525
    c = 1013904223
    x = seed
    tr = []

    ix = 0
    while ix < nSamples:
        x = (a * x + c) %  m
        tr = tr + [float(x) / float(m)]
        ix = ix + 1

    return tr

def generate_data(nSamples, nColumns=None, coefficients=None, seed=42):
    if nColumns is None:
        assert coefficients is not None, "coef is None"
        nColumns = len(coefficients)
    if coefficients is None:
        assert nColumns is not None, "nColumns is None"
        coefficients = range(nColumns)

    X = generate_random_x(seed, nSamples, nColumns)

    y = generate_random_y(X, coefficients, seed + nColumns)

    return X, y

class LogisticBenchmarkTest(unittest.TestCase,
                            ExecutorTestCommon.ExecutorTestCommon):
    @classmethod
    def setUpClass(cls):
        cls.executor = None

    @classmethod
    def tearDownClass(cls):
        if cls.executor is not None:
            cls.executor.close()

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return InMemorySimulationExecutorFactory.create_executor()
        if cls.executor is None:
            cls.executor = InMemorySimulationExecutorFactory.create_executor()
            cls.executor.stayOpenOnExit = True

        return cls.executor

    def nRowsFromMbOfData(self, mbOfData, nColumns):
        return int(mbOfData * 1024.0 * 1024.0 / 8.0 / nColumns)

    @PerformanceTestReporter.PerfTest("pyfora.trust_region_solver.2MB.20Col")
    def test_trust_region_perf_purePython_1(self):
        self.trust_region_perf(2, 20)
    
    @PerformanceTestReporter.PerfTest("pyfora.trust_region_solver.20MB.20Col")
    def test_trust_region_perf_purePython_2(self):
        self.trust_region_perf(20, 20)
    
    @PerformanceTestReporter.PerfTest("pyfora.trust_region_solver.2MB.100Col")
    def test_trust_region_perf_purePython_3(self):
        self.trust_region_perf(2, 100)
    
    @PerformanceTestReporter.PerfTest("pyfora.trust_region_solver.20MB.100Col")
    def test_trust_region_perf_purePython_4(self):
        self.trust_region_perf(20, 100)
    
    def trust_region_perf(self, mbOfData, nColumns):
        executor = self.create_executor()

        nRows = self.nRowsFromMbOfData(mbOfData, nColumns)

        print "generating data ... "
        data = executor.submit(generate_data, nRows, nColumns)

        regularization_strength = 1.0

        for ct in xrange(1, 5):
            print "computing in pyfora ..."
            t0 = time.time()

            with executor.remotely:
                res = 0
                x, y = data

                for ix in xrange(ct):
                    fit = BinaryLogisticRegressionFitter(
                        1.0 / len(x) / regularization_strength,
                        False,
                        "newton-cg",
                        1.0,
                        1e-4 + ix / 1000000.0,
                        1000
                        ).fit(x, y)
                    coef = fit.coefficients
                    iters = fit.iters
                    res = res + coef[0]
                    res = res + ix
            elapsed_time = time.time() - t0
            print "*** Ct %s *** : pyfora computed coefficients =\n%s,\n"\
                "iters = %s, %s times in %s sec, for an avg time of %s sec / fit\n" % (
                    ct,
                    coef.toLocal().result(),
                    iters.toLocal().result(),
                    ct,
                    elapsed_time,
                    elapsed_time / ct)
