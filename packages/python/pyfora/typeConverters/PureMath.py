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


class Sqrt:
    def __call__(self, val):
        if val < 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.sqrt(val.@m))
                   }"""
            )(val)


class Hypot:
    def __call__(self, val1, val2):
        return __inline_fora(
            """fun(val1, val2) {
                   PyFloat(math.hypot(val1.@m, val2.@m))
                   }"""
            )(val1, val2)


class Log:
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log(val.@m))
                   }"""
            )(val)


class Acos:
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.acos(val.@m))
                   }"""
            )(val)


class Acosh:
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.acosh(val.@m))
                   }"""
            )(val)


class Cos:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.cos(val.@m))
                   }"""
            )(val)


class Cosh:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.cosh(val.@m))
                   }"""
            )(val)


class Asin:
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.asin(val.@m))
                   }"""
            )(val)


class Asinh:
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.asinh(val.@m))
                   }"""
            )(val)


class Sin:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.sin(val.@m))
                   }"""
            )(val)


class Sinh:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.sinh(val.@m))
                   }"""
            )(val)


class Atan:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atan(val.@m))
                   }"""
            )(val)


class Atan2:
    def __call__(self, val1, val2):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atan2(val1.@m, val2.@m))
                   }"""
            )(val1, val2)


class Atanh:
    def __call__(self, val):
        if val >= 1:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.atanh(val.@m))
                   }"""
            )(val)


class Tan:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.tan(val.@m))
                   }"""
            )(val)


class Tanh:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.tanh(val.@m))
                   }"""
            )(val)


class Ceil:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.ceil(val.@m))
                   }"""
            )(val)


class Erf:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.erf(val.@m))
                   }"""
            )(val)


class Erfc:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.erfc(val.@m))
                   }"""
            )(val)


class Exp:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.exp(val.@m))
                   }"""
            )(val)


class Expm1:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.expm1(val.@m))
                   }"""
            )(val)


class Factorial:
    def __call__(self, val):
        if Floor()(val) != val or val < 0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.factorial(val.@m))
                   }"""
            )(val)


class Floor:
    def __call__(self, val):
        return __inline_fora(
            """fun(val) {
                   PyFloat(math.floor(val.@m))
                   }"""
            )(val)


class Lgamma:
    def __call__(self, val):
        if val <= -1 or val == 0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.lgamma(val.@m))
                   }"""
            )(val)


class Log10:
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log_10(val.@m))
                   }"""
            )(val)


class Log1p:
    def __call__(self, val):
        if val < -1:
            raise ValueError("math domain error")

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log1p(val.@m))
                   }"""
            )(val)


def generateMappings():
    import math
    
    mappings_ = [
        (math.sqrt, Sqrt), (math.hypot, Hypot), (math.log, Log), (math.cos, Cos),
        (math.sin, Sin), (math.tan, Tan), (math.cosh, Cosh), (math.sinh, Sinh),
        (math.tanh, Tanh), (math.acosh, Acosh), (math.asinh, Asinh),
        (math.atanh, Atanh), (math.acos, Acos), (math.asin, Asin),
        (math.atan, Atan), (math.atan2, Atan2), (math.ceil, Ceil), (math.erf, Erf),
        (math.erfc, Erfc), (math.exp, Exp), (math.expm1, Expm1),
        (math.factorial, Factorial), (math.floor, Floor), (math.lgamma, Lgamma),
        (math.log, Log), (math.log10, Log10), (math.log1p, Log1p)
    ]

    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
          (instance, pureType) in mappings_]

    return tr


