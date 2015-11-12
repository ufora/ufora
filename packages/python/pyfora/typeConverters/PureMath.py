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
        return Sqrt.__pyfora_builtins__.math.sqrt(val)


class Hypot:
    def __call__(self, val1, val2):
        return Hypot.__pyfora_builtins__.math.hypot(val1, val2)


class Log:
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")
        return Log.__pyfora_builtins__.math.log(val)


class Acos:
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return Acos.__pyfora_builtins__.math.acos(val)


class Acosh:
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return Acosh.__pyfora_builtins__.math.acosh(val)


class Cos:
    def __call__(self, val):
        return Cos.__pyfora_builtins__.math.cos(val)


class Cosh:
    def __call__(self, val):
        return Cosh.__pyfora_builtins__.math.cosh(val)


class Asin:
    def __call__(self, val):
        if val > 1.0 or val < -1.0:
            raise ValueError("math domain error")

        return Asin.__pyfora_builtins__.math.asin(val)


class Asinh:
    def __call__(self, val):
        if val < 1.0:
            raise ValueError("math domain error")

        return Asinh.__pyfora_builtins__.math.asinh(val)


class Sin:
    def __call__(self, val):
        return Sin.__pyfora_builtins__.math.sin(val)


class Sinh:
    def __call__(self, val):
        return Cosh.__pyfora_builtins__.math.sinh(val)


class Atan:
    def __call__(self, val):
        return Atan.__pyfora_builtins__.math.atan(val)


class Atan2:
    def __call__(self, val1, val2):
        return Atan2.__pyfora_builtins__.math.atan2(val1, val2)


class Atanh:
    def __call__(self, val):
        if val >= 1:
            raise ValueError("math domain error")
        return Atanh.__pyfora_builtins__.math.atanh(val)


class Tan:
    def __call__(self, val):
        return Tan.__pyfora_builtins__.math.tan(val)


class Tanh:
    def __call__(self, val):
        return Tanh.__pyfora_builtins__.math.tanh(val)


class Ceil:
    def __call__(self, val):
        return Ceil.__pyfora_builtins__.math.ceil(val)


class Erf:
    def __call__(self, val):
        return Erf.__pyfora_builtins__.math.erf(val)


class Erfc:
    def __call__(self, val):
        return Erfc.__pyfora_builtins__.math.erfc(val)


class Exp:
    def __call__(self, val):
        return Exp.__pyfora_builtins__.math.exp(val)


class Expm1:
    def __call__(self, val):
        return Expm1.__pyfora_builtins__.math.expm1(val)


class Factorial:
    def __call__(self, val):
        if Floor()(val) != val or val < 0:
            raise ValueError("math domain error")
        return Factorial.__pyfora_builtins__.math.factorial(val)


class Floor:
    def __call__(self, val):
        return Floor.__pyfora_builtins__.math.floor(val)


class Lgamma:
    def __call__(self, val):
        if val <= -1 or val == 0:
            raise ValueError("math domain error")
        return Lgamma.__pyfora_builtins__.math.lgamma(val)


class Log10:
    def __call__(self, val):
        if val <= 0.0:
            raise ValueError("math domain error")
        return Log10.__pyfora_builtins__.math.log10(val)


class Log1p:
    def __call__(self, val):
        if val < -1:
            raise ValueError("math domain error")
        return Log1p.__pyfora_builtins__.math.log1p(val)


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


