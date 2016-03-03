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

import pandas
import numpy.testing


from pyfora.algorithms.logistic.TrustRegionConjugateGradientSolver \
    import TrustRegionConjugateGradientSolver


class TrustRegionTests(object):
    def trustRegionData(self):
        X = pandas.DataFrame({'A': [-1,0,1], 'B': [0,1,1]})
        y = pandas.Series([1,-1,-1])
        return X, y

    def solve(self, X, y, classZeroLabel, C=1):
        def f(X, y, C):
            return TrustRegionConjugateGradientSolver(
                X, y, classZeroLabel, C).solve()

        return self.evaluateWithExecutor(f, X, y, C)

    def test_trust_region_1(self):
        X, y = self.trustRegionData()

        res = self.solve(X, y, 1)

        # results checked against liblinear, scikit themselves.
        scikit_weights = [-0.59106183, -0.59106183]
        numpy.testing.assert_allclose(res.weights, scikit_weights,
                                      atol=1e-4, rtol=1e-4)
        self.assertEqual(res.iterations, 2)
            
    def test_trust_region_2(self):
        X, y = self.trustRegionData()

        C = 1.0 / len(y)

        res = self.solve(X, y, 1, C)
        numpy.testing.assert_allclose(
            res.weights,
            [-0.26760031, -0.26760031]
            )
        self.assertEqual(res.iterations, 2)

    def test_trust_region_3(self):
        # corresponds to the fora test: logisticregressionTests.basic_2

        X = pandas.DataFrame(
            [[-0.25091976,  0.90142861],
             [ 0.46398788,  0.19731697],
             [-0.68796272, -0.68801096],
             [-0.88383278,  0.73235229],
             [ 0.20223002,  0.41614516]]
            )
        y = pandas.Series([1,-1,-1,-1,1])

        C = 1.0 / len(X) / 0.01

        res = self.solve(X, y, 1, C)
        numpy.testing.assert_allclose(
            res.weights,
            [1.55340616, 1.28486523]
            )

    def test_trust_region_4(self):
        # corresponds to the fora test: logisticregressionTests.basic_3

        X = pandas.DataFrame(
            {'A': [-0.25091976, 0.46398788, -0.68796272],
             'B': [0.90142861, 0.19731697, -0.68801096]})

        y = pandas.Series([1, -1, -1])

        C = 1.0 / len(X) / 0.01

        res = self.solve(X, y, 1, C)

        numpy.testing.assert_allclose(
            res.weights,
            [-1.78096818,  3.42088899]
            )
        
    def test_trust_region_5(self):
        # corresponds to the fora test: logisticregressionTests.basic_4

        X = pandas.DataFrame(
            [[-0.25091976,  0.90142861],
             [ 0.46398788,  0.19731697],
             [-0.68796272, -0.68801096],
             [-0.88383278,  0.73235229],
             [ 0.20223002,  0.41614516],
             [-0.95883101,  0.9398197 ],
             [ 0.66488528, -0.57532178],
             [-0.63635007, -0.63319098],
             [-0.39151551,  0.04951286],
             [-0.13610996, -0.41754172]]
            )
        y = pandas.Series([1, -1, -1, 1, 1, 1, -1, 1, 1, -1])

        C = 1.0 / len(X) / 0.01

        res = self.solve(X, y, 1, C)

        numpy.testing.assert_allclose(
            res.weights,
            [-2.42814882,  2.69715838]
            )
