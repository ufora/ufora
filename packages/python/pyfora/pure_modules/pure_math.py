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

import math
from pyfora.PureImplementationMapping import pureMapping


@pureMapping(math.sqrt)
class Sqrt(object):
    def __call__(self, val):
        if val < 0.0:
            raise ValueError("math domain error")

        return val ** 0.5


@pureMapping(math.hypot)
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


@pureMapping(math.log)
class Log(object):
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.log(val.@m))
                   }"""
            )(val)


@pureMapping(math.acos)
class Acos(object):
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.acos(val.@m))
                   }"""
            )(val)


@pureMapping(math.acosh)
class Acosh(object):
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.acosh(val.@m))
                   }"""
            )(val)


@pureMapping(math.cos)
class Cos(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.cos(val.@m))
                   }"""
            )(val)


@pureMapping(math.cosh)
class Cosh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.cosh(val.@m))
                   }"""
            )(val)


@pureMapping(math.asin)
class Asin(object):
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.asin(val.@m))
                   }"""
            )(val)


@pureMapping(math.asinh)
class Asinh(object):
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.asinh(val.@m))
                   }"""
            )(val)


@pureMapping(math.sin)
class Sin(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.sin(val.@m))
                   }"""
            )(val)


@pureMapping(math.sinh)
class Sinh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.sinh(val.@m))
                   }"""
            )(val)


@pureMapping(math.atan)
class Atan(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.atan(val.@m))
                   }"""
            )(val)


@pureMapping(math.atan2)
class Atan2(object):
    def __call__(self, val1, val2):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.atan2(val1.@m, val2.@m))
                   }"""
            )(val1, val2)


@pureMapping(math.atanh)
class Atanh(object):
    def __call__(self, val):
        if val >= 1:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.atanh(val.@m))
                   }"""
            )(val)


@pureMapping(math.tan)
class Tan(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.tan(val.@m))
                   }"""
            )(val)


@pureMapping(math.tanh)
class Tanh(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.tanh(val.@m))
                   }"""
            )(val)


@pureMapping(math.ceil)
class Ceil(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.ceil(val.@m))
                   }"""
            )(val)


@pureMapping(math.erf)
class Erf(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.erf(val.@m))
                   }"""
            )(val)


@pureMapping(math.erfc)
class Erfc(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.erfc(val.@m))
                   }"""
            )(val)


@pureMapping(math.exp)
class Exp(object):
    def __call__(self, val):
        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.exp(val.@m))
                   }"""
            )(val)


@pureMapping(math.expm1)
class Expm1(object):
    def __call__(self, x):
        # if very small, return first three terms of taylor expansion
        if abs(x) < 1e-5:
            return x + 0.5 * x * x

        return math.exp(x) - 1.0


@pureMapping(math.factorial)
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


@pureMapping(math.floor)
class Floor(object):
    def __call__(self, x):
        remainder = math.fmod(x, 1)

        if x >= 0:
            return float(x - remainder)

        if remainder == 0:
            return float(x)

        return float(x - remainder - 1)


@pureMapping(math.fmod)
class Fmod(object):
    def __call__(self, x, y):
        if not isinstance(x, float):
            x = float(x)
        if not isinstance(y, float):
            y = float(y)

        return __inline_fora(
            """fun(@unnamed_args:(x, y), *args) {
                   return PyFloat(`fmod(x.@m, y.@m))
                   }"""
            )(x, y)


@pureMapping(math.lgamma)
class Lgamma(object):
    def __call__(self, val):
        if val <= -1 or val == 0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.lgamma(val.@m))
                   }"""
            )(val)


@pureMapping(math.log10)
class Log10(object):
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.log_10(val.@m))
                   }"""
            )(val)


@pureMapping(math.log1p)
class Log1p(object):
    def __call__(self, x):
        if x <= -1:
            raise ValueError("math domain error")

        t = float(1.0 + x)
        # if very small, x serves as good approximation
        if t == 1.0:
            return x

        return math.log(t) * (x / (t - 1.0))

