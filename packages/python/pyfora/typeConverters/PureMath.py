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


import math


class Sqrt(object):
    def __call__(self, val):
        if val < 0.0:
            raise ValueError("math domain error")
            
        return val ** 0.5

class Hypot(object):
    def __call__(self, x, y):
        x = abs(float(x))
        y = abs(float(y))

        if x == 0:
            return y
        if y == 0:
            return x

        t = min(x, y)
        x = max(x, y)
        y = t

        return x * (1.0 + (y / x) * (y / x)) ** 0.5

class Log(object):
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log(val.@m))
                   }"""
            )(val)


class Acos(object):
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.acos(val.@m))
                   }"""
            )(val)


class Acosh(object):
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.acosh(val.@m))
                   }"""
            )(val)


class Cos(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.cos(val.@m))
                   }"""
            )(val)


class Cosh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.cosh(val.@m))
                   }"""
            )(val)


class Asin(object):
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.asin(val.@m))
                   }"""
            )(val)


class Asinh(object):
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.asinh(val.@m))
                   }"""
            )(val)


class Sin(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.sin(val.@m))
                   }"""
            )(val)


class Sinh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.sinh(val.@m))
                   }"""
            )(val)


class Atan(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atan(val.@m))
                   }"""
            )(val)


class Atan2(object):
    def __call__(self, val1, val2):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atan2(val1.@m, val2.@m))
                   }"""
            )(val1, val2)


class Atanh(object):
    def __call__(self, val):
        if val >= 1:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atanh(val.@m))
                   }"""
            )(val)


class Tan(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.tan(val.@m))
                   }"""
            )(val)


class Tanh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.tanh(val.@m))
                   }"""
            )(val)


class Ceil(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.ceil(val.@m))
                   }"""
            )(val)


class Erf(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.erf(val.@m))
                   }"""
            )(val)


class Erfc(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.erfc(val.@m))
                   }"""
            )(val)


class Exp(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.exp(val.@m))
                   }"""
            )(val)


class Expm1(object):
    def __call__(self, x):
        # if very small, return first three terms of taylor expansion
        if abs(x) < 1e-5:
            return x + 0.5 * x * x

        return math.exp(x) - 1.0


class Factorial(object):
    def __call__(self, val):
        if not math.floor(val) == val:
            raise ValueError(
                "factorial() only accepts integral values"
                )

        if val < 0:
            raise ValueError(
                "factorial() not defined for negative values"
                )

        ix = 1
        res = 1
        while ix <= val:
            res = res * ix
            ix = ix + 1

        return res


class Floor(object):
    def __call__(self, x):
        remainder = math.fmod(x, 1)

        if x >= 0:
            return float(x - remainder)

        if remainder == 0:
            return float(x)

        return float(x - remainder - 1)


class Fmod(object):
    def __call__(self, x, y):
        if not isinstance(x, float):
            x = float(x)
        if not isinstance(y, float):
            y = float(y)

        return __inline_fora(
            """fun(x, y) {
                   return PyFloat(`fmod(x.@m, y.@m))
                   }"""
            )(x, y)


class Lgamma(object):
    def __call__(self, val):
        if val <= -1 or val == 0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.lgamma(val.@m))
                   }"""
            )(val)


class Log10(object):
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log_10(val.@m))
                   }"""
            )(val)


class Log1p(object):
    def __call__(self, x):
        if x <= -1:
            raise ValueError("math domain error")

        t = float(1.0 + x)
        # if very small, x serves as good approximation
        if t == 1.0:
            return x

        return math.log(t) * (x / (t - 1.0))


def generateMappings():
    mappings_ = [
        (math.sqrt, Sqrt), (math.hypot, Hypot), (math.log, Log), (math.cos, Cos),
        (math.sin, Sin), (math.tan, Tan), (math.cosh, Cosh), (math.sinh, Sinh),
        (math.tanh, Tanh), (math.acosh, Acosh), (math.asinh, Asinh),
        (math.atanh, Atanh), (math.acos, Acos), (math.asin, Asin),
        (math.atan, Atan), (math.atan2, Atan2), (math.ceil, Ceil), (math.erf, Erf),
        (math.erfc, Erfc), (math.exp, Exp), (math.expm1, Expm1),
        (math.factorial, Factorial), (math.floor, Floor), (math.lgamma, Lgamma),
        (math.log, Log), (math.log10, Log10), (math.log1p, Log1p),
        (math.fmod, Fmod)
    ]

    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
          (instance, pureType) in mappings_]

    return tr


