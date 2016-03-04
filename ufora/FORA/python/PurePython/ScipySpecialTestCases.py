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


import numpy
import numpy.testing
import scipy.special


class ScipySpecialTestCases(object):
    def test_beta(self):
        def f(a, b):
            return scipy.special.beta(a, b)

        a = 1.0
        b = 2.0
        numpy.testing.assert_almost_equal(
            f(a, b),
            self.evaluateWithExecutor(f, a, b)
            )

    def test_gamma(self):
        def f(x):
            return scipy.special.gamma(x)

        for val in [-0.5, 0.5, 1.0]:
            self.assertTrue(
                numpy.isclose(
                    f(val),
                    self.evaluateWithExecutor(f, val)
                    )
                )

    def test_hyp2f1_1(self):
        def f(a, b, c, z):
            return scipy.special.hyp2f1(a, b, c, z)

        a, b, c, z = 1, 1, 2, -1
        self.assertTrue(
            numpy.isclose(
                f(a, b, c, z),
                self.evaluateWithExecutor(f, a, b, c, z)
                )
            )

    def test_hyp2f1_2(self):
        def f(a, b, c, z):
            return scipy.special.hyp2f1(a, b, c, z)

        a,b,c,z = 2.8346157367796936, 0.0102, 3.8346157367796936, 0.9988460588541513

        res1 = self.evaluateWithExecutor(f, a, b, c, z)
        res2 = f(a, b, c, z)

        numpy.testing.assert_almost_equal(
            res1,
            res2
            )

        numpy.testing.assert_almost_equal(
            res1,
            1.0182383750413575
            )

    def test_gammaln_1(self):
        def f(x):
            return scipy.special.gammaln(x)

        for val in [-2, -1.3, -1, -0.5, 0.0, 0.5, 1, 2.1, 3]:
            self.assertTrue(
                numpy.isclose(
                    f(val),
                    self.evaluateWithExecutor(f, val)
                    )
                )

    def test_gammaln_2(self):
        def f():
            gamln = scipy.special.gammaln(3)
            lngam = numpy.log(scipy.special.gamma(3))
            return gamln, lngam

        gamln, lngam = self.evaluateWithExecutor(f)

        numpy.testing.assert_almost_equal(gamln,lngam,8)

        gamln2, lngam2 = f()

        numpy.testing.assert_almost_equal(gamln, gamln2)
        numpy.testing.assert_almost_equal(lngam, lngam2)

    def test_betaln_1(self):
        def f(a, b):
            return scipy.special.betaln(a, b)

        numpy.testing.assert_equal(
            self.evaluateWithExecutor(f, 1, 1),
            0.0
            )
        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f, -100.3, 1e-200),
            scipy.special.gammaln(1e-200)
            )
        # note: we're not quite as accurate as scipy here.
        # scipy can get this to rtol=1e-13
        numpy.testing.assert_allclose(
            self.evaluateWithExecutor(f, 0.0342, 170),
            3.1811881124242447,
            rtol=1e-13, atol=0
            )

    def test_betaln_2(self):
        def f(a, b):
            return scipy.special.betaln(a, b)

        res1 = self.evaluateWithExecutor(f, 2, 4)
        res2 = numpy.log(abs(scipy.special.beta(2,4)))

        numpy.testing.assert_almost_equal(res1, res2, 8)


    def test_scipy_floor(self):
        def f(x):
            return scipy.floor(x)

        res1 = self.evaluateWithExecutor(f, 1.43)
        res2 = f(1.43)

        numpy.testing.assert_almost_equal(res1, res2, 8)
