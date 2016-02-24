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


import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.typeConverters.PureMath as PureMath
import pyfora.typeConverters.PureNumpy as PureNumpy
import pyfora.BuiltinPureImplementationMappings as BuiltinPureImplementationMappings


import math
import numpy
import scipy
import scipy.special


class BetaFunction(object):
    def __call__(self, a, b):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        
        return __inline_fora(
            """fun(PyFloat(...) a, PyFloat(...) b) { 
                   return PyFloat(`cephes_beta(a.@m, b.@m))
                   }"""
            )(a, b)


class GammaFunction(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(x) {
                   return PyFloat(`tgamma(x.@m))
                   }"""
            )(x)


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
            """fun(a, b, c, z) {
                   return PyFloat(`hyp2f1(a.@m, b.@m, c.@m, z.@m))
                   }"""
            )(a, b, c, z)


class Digamma(object):
    def __call__(self, z):
        if not isinstance(z, float):
            z = float(z)

        return __inline_fora(
            """fun(z) {
                   return PyFloat(`digamm(z.@m));
                   }"""
            )(z)


class Erfcinv(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(x) {
                   return PyFloat(math.erfcinv(x.@m))
                   }"""
            )(x)


class Erfinv(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(x) {
                   return PyFloat(math.erfinv(x.@m))
                   }"""
            )(x)


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
            

class Betaincinv(object):
    def __call__(self, a, b, y):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        if not isinstance(y, float):
            y = float(y)

        return __inline_fora(
            """fun(a, b, y) {
                   return PyFloat(`ibeta(a.@m, b.@m, y.@m))
                   }"""
            )(a, b, y)


class GammaLn(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        if x <= 0 and math.ceil(x) == x:
            return numpy.inf

        return __inline_fora(
            """fun(x) {
                   return PyFloat(`lgamma(x.@m))
                   }"""
            )(x)


class BetaLn(object):
    def __call__(self, a, b):
        if not isinstance(a, float):
            a = float(a)
        if not isinstance(b, float):
            b = float(b)
        
        return __inline_fora(
            """fun(PyFloat(...) a, PyFloat(...) b) { 
                   return PyFloat(`cephes_lbeta(a.@m, b.@m))
                   }"""
            )(a, b)


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
            """fun(n, x) {
                   return PyFloat(`cyl_bessel_k(n.@m, x.@m))
                   }"""
            )(n, x)


class Iv(object):
    "Modified Bessel function of the first kind of real order v"
    def __call__(self, v, z):
        if not isinstance(v, int):
            v = int(v)
        if not isinstance(z, float):
            z = float(z)

        return __inline_fora(
            """fun(v, z) {
                   return PyFloat(`cyl_bessel_i(v.@m, z.@m))
                   }"""
            )(v, z)


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


class Expit(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return 1.0 / (1.0 + scipy.exp(-x))


def generateMappings():
    tr = []

    # some of these creatures need "vectorized" forms, as in scipy they're 
    # really "ufunc"s
    mappings_ = [
        (scipy.special.beta, BetaFunction), (scipy.special.gamma, GammaFunction),
        (scipy.special.hyp2f1, Hyp2f1), (scipy.special.erf, PureMath.Erf),
        (scipy.special.expm1, PureMath.Expm1),
        (scipy.special.digamma, Digamma),
        (scipy.special.psi, Digamma),
        (scipy.special.erfc, PureMath.Erfc), (scipy.special.erfcinv, Erfcinv),
        (scipy.special.erfinv, Erfinv), (scipy.special.betainc, Betainc),
        (scipy.special.gammaln, GammaLn),
        (scipy.special.betaln, BetaLn),
        (scipy.special.log1p, PureNumpy.Log1p),
        (scipy.special.kn, Kn), (scipy.special.iv, Iv),
        (scipy.special.comb, Comb), (scipy.special.factorial, PureMath.Factorial),
        (scipy.special.logit, Logit), (scipy.special.expit, Expit),
        (scipy.special.round, BuiltinPureImplementationMappings.Round),
        (scipy.floor, PureMath.Floor),
        (scipy.log, PureNumpy.Log),
        (scipy.log1p, PureNumpy.Log1p),
        (scipy.exp, PureMath.Exp), (scipy.expm1, PureMath.Expm1),
        (scipy.sqrt, PureMath.Sqrt), (scipy.hypot, PureMath.Hypot),
        (scipy.cos, PureMath.Cos), (scipy.sin, PureMath.Sin), (scipy.tan, PureMath.Tan),
        (scipy.cosh, PureMath.Cosh), (scipy.sinh, PureMath.Sinh), (scipy.tan, PureMath.Tanh),
        (scipy.isnan, PureNumpy.IsNan)
        ]

    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
          (instance, pureType) in mappings_]

    return tr
    
    
