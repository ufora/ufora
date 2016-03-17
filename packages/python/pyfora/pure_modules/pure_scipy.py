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


from pyfora.PureImplementationMapping import pureMapping
import pyfora.pure_modules.pure_math as PureMath
import pyfora.pure_modules.pure_numpy as PureNumpy
from pyfora.pure_modules.pure___builtin__ import Round


import math
import numpy
import scipy
import scipy.special
import scipy.linalg


@pureMapping(scipy.linalg.expm)
class Expm:
    def __call__(self, A):
        errString = "can only call scipy.linalg.expm on square arrays"
        if not isinstance(A, PureNumpy.PurePythonNumpyArray):
            raise TypeError(errString)
        if A.shape[0] != A.shape[1]:
            raise TypeError(errString)
            
        result = __inline_fora(
            """fun(@unnamed_args:(matrix), *args) {
                   return purePython.linalgModule.expm(
                       matrix
                       )
                   }"""
            )(A)

        return PureNumpy.PurePythonNumpyArray(
            tuple(result[1]),
            result[0]
            )


@pureMapping(scipy.special.beta)
class BetaFunction(object):
    def __call__(self, a, b):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)

        return __inline_fora(
            """fun(@unnamed_args:(PyFloat(...) a, PyFloat(...) b), *args) {
                   return PyFloat(`cephes_beta(a.@m, b.@m))
                   }"""
            )(a, b)


@pureMapping(scipy.special.gamma)
class GammaFunction(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(x), *args) {
                   return PyFloat(`tgamma(x.@m))
                   }"""
            )(x)


@pureMapping(scipy.special.hyp2f1)
class Hyp2f1(object):
    def __call__(self, a, b, c, z):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        if not isinstance(c, float):
            c = float(c)
        if not isinstance(z, float):
            z = float(z)

        return __inline_fora(
            """fun(@unnamed_args:(a, b, c, z), *args) {
                   return PyFloat(`hyp2f1(a.@m, b.@m, c.@m, z.@m))
                   }"""
            )(a, b, c, z)


@pureMapping(scipy.special.digamma)
@pureMapping(scipy.special.psi)
class Digamma(object):
    def __call__(self, z):
        if not isinstance(z, float):
            z = float(z)

        return __inline_fora(
            """fun(@unnamed_args:(z), *args) {
                   return PyFloat(`digamm(z.@m));
                   }"""
            )(z)


@pureMapping(scipy.special.erfcinv)
class Erfcinv(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args(x), *args) {
                   return PyFloat(math.erfcinv(x.@m))
                   }"""
            )(x)


@pureMapping(scipy.special.erfinv)
class Erfinv(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(x), *args) {
                   return PyFloat(math.erfinv(x.@m))
                   }"""
            )(x)


@pureMapping(scipy.special.betainc)
class Betainc(object):
    def __call__(self, a, b, x):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(a, b, x) {
                   return PyFloat(`ibeta(a.@m, b.@m, x.@m))
                   }"""
            )(a, b, x)


@pureMapping(scipy.special.betaincinv)
class Betaincinv(object):
    def __call__(self, a, b, y):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        if not isinstance(y, float):
            y = float(y)

        return __inline_fora(
            """fun(@unnamed_args:(a, b, y), *args) {
                   return PyFloat(`ibeta(a.@m, b.@m, y.@m))
                   }"""
            )(a, b, y)


@pureMapping(scipy.special.gammaln)
class GammaLn(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        if x <= 0 and math.ceil(x) == x:
            return numpy.inf

        return __inline_fora(
            """fun(@unnamed_args:(x), *args) {
                   return PyFloat(`lgamma(x.@m))
                   }"""
            )(x)


@pureMapping(scipy.special.betaln)
class BetaLn(object):
    def __call__(self, a, b):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)

        return __inline_fora(
            """fun(@unnamed_args:(PyFloat(...) a, PyFloat(...) b), *args) {
                   return PyFloat(`cephes_lbeta(a.@m, b.@m))
                   }"""
            )(a, b)


@pureMapping(scipy.special.kn)
class Kn(object):
    """Modified Bessel function of the second kind of integer order n
       Returns the modified Bessel function of the second kind for
       integer order n at real x."""
    def __call__(self, n, x):
        if not isinstance(n, int):
            n = int(n)
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(n, x), *args) {
                   return PyFloat(`cyl_bessel_k(n.@m, x.@m))
                   }"""
            )(n, x)


@pureMapping(scipy.special.iv)
class Iv(object):
    "Modified Bessel function of the first kind of real order v"
    def __call__(self, v, z):
        if not isinstance(v, int):
            v = int(v)
        if not isinstance(z, float):
            z = float(z)

        return __inline_fora(
            """fun(@unnamed_args:(v, z), *args) {
                   return PyFloat(`cyl_bessel_i(v.@m, z.@m))
                   }"""
            )(v, z)


@pureMapping(scipy.special.comb)
class Comb(object):
    def __call__(self, n, k):
        if not isinstance(n, int):
            n = int(n)
        if not isinstance(k, int):
            k = int(k)

        res = 1.0
        if n < 0 or k < 0:
            return 0.0

        if k == 0:
            return res

        if (n - k) < k:
            return scipy.special.comb(n, n - k)

        for ix in xrange(k):
            res = (res * (n - ix)) / (k - ix)

        return res


@pureMapping(scipy.special.logit)
class Logit(object):
    def __call__(self, p):
        if not isinstance(p, float):
            p = float(p)

        if p < 0 or p > 1:
            return scipy.nan

        if p == 0:
            return -scipy.inf

        if p == 1:
            return scipy.inf

        return scipy.log(p / (1.0 - p))


@pureMapping(scipy.special.expit)
class Expit(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return 1.0 / (1.0 + scipy.exp(-x))

@pureMapping(scipy.special.erf)
class ScipyErf(object):
    def __call__(self, x):
        return PureMath.Erf()(x)


@pureMapping(scipy.special.erfc)
class ScipyErfc(object):
    def __call__(self, x):
        return PureMath.Erfc()(x)


@pureMapping(scipy.special.expm1)
class ScipySpecialExpm1(object):
    def __call__(self, x):
        return PureMath.Expm1()(x)


@pureMapping(scipy.special.log1p)
class ScipySpecialLog1p(PureNumpy.Log1p): pass


@pureMapping(scipy.special.factorial)
class ScipyFactorial(PureMath.Factorial): pass


@pureMapping(scipy.special.round)
class ScipyRound(Round): pass


@pureMapping(scipy.floor)
class ScipyFloor(PureMath.Floor): pass


@pureMapping(scipy.log)
class ScipyLog(PureNumpy.Log): pass


@pureMapping(scipy.log1p)
class ScipyLog1p(PureNumpy.Log1p): pass


@pureMapping(scipy.exp)
class ScipyExp(PureMath.Exp): pass


@pureMapping(scipy.expm1)
class ScipyExpm1(PureMath.Expm1): pass


@pureMapping(scipy.sqrt)
class ScipySqrt(PureMath.Sqrt): pass


@pureMapping(scipy.hypot)
class ScipytHypot(PureMath.Hypot): pass


@pureMapping(scipy.cos)
class ScipyCos(PureMath.Cos): pass


@pureMapping(scipy.sin)
class ScipySin(PureMath.Sin): pass


@pureMapping(scipy.tan)
class ScipyTan(PureMath.Tan): pass


@pureMapping(scipy.cosh)
class ScipytCosh(PureMath.Cosh): pass


@pureMapping(scipy.sinh)
class ScipySinh(PureMath.Sinh): pass


@pureMapping(scipy.tanh)
class ScipyTanh(PureMath.Tanh): pass


@pureMapping(scipy.isnan)
class ScipyIsNan(PureNumpy.IsNan): pass
