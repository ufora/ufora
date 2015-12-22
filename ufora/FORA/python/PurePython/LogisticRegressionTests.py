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
import pyfora.algorithms.util
from pyfora.algorithms.BinaryLogisticRegressionFitter import BinaryLogisticRegressionFitter


class LogisticRegressionTests(object):
    def test_unique(self):
        x = [5,5,4,2,4,2,1,3,3,5,6]
        def f():
            return pyfora.algorithms.util.unique(x)

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
            return fit

        res = self.evaluateWithExecutor(f)

        expectedResult = numpy.array([0.26901034, 0.25372016, 0.10102151])
        
        self.assertTrue(
            numpy.allclose(
                res[0],
                expectedResult,
                rtol=0.1
                )
            )

