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

import pandas
import numpy


import pyfora.Exceptions
from pyfora.unique import unique
from pyfora.algorithms import BinaryLogisticRegressionFitter


class LogisticRegressionTests(object):
    def test_unique(self):
        x = [5,5,4,2,4,2,1,3,3,5,6]
        def f():
            return unique(x)

        self.assertEqual(
            self.evaluateWithExecutor(f),
            list(set(x))
            )

    def exampleData(self):
        X = pandas.DataFrame({'A': [-1,0,1], 'B': [0,1,1]})
        y = pandas.DataFrame({'C': [0,1,1]})
        return X, y

    def test_binary_logistic_regression_coefficients(self):
        X, y = self.exampleData()

        def f():
            fit = BinaryLogisticRegressionFitter(1).fit(X, y)
            return fit.intercept, fit.coefficients

        computedIntercept, computedCoefficients = self.evaluateWithExecutor(f)

        expectedIntercept = 0.10102151
        expectedCoefficients = numpy.array([0.26901034, 0.25372016])

        self.assertTrue(
            numpy.isclose(
                computedIntercept,
                expectedIntercept,
                rtol=0.1
                )
            )

        self.assertTrue(
            numpy.allclose(
                computedCoefficients,
                expectedCoefficients,
                rtol=0.1
                )
            )

    def test_binary_logistic_regression_probabilities(self):
        X, y = self.exampleData()

        def f():
            fit = BinaryLogisticRegressionFitter(1).fit(X, y)
            return fit.predict_probability(X)

        expectedPredictedProbabilities = [0.541898928, 0.4122333, 0.34892898]
        computedProbabilities = self.evaluateWithExecutor(f)

        self.assertTrue(
            numpy.allclose(
                computedProbabilities,
                expectedPredictedProbabilities,
                rtol=0.1
                )
            )

    def test_binary_logistic_regression_predict(self):
        X, y = self.exampleData()

        def f():
            fit = BinaryLogisticRegressionFitter(1).fit(X, y)
            return fit.predict(X)

        self.assertTrue(
            numpy.array_equal(
                self.evaluateWithExecutor(f),
                numpy.array([0, 1, 1])
                )
            )

    def test_binary_logistic_regression_score(self):
        X, y = self.exampleData()

        def f():
            fit = BinaryLogisticRegressionFitter(1).fit(X, y)
            return fit.score(X, y)

        self.assertEqual(self.evaluateWithExecutor(f), 1.0)
