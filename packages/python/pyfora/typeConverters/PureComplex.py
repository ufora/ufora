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

class PurePythonComplex(object):
    def __init__(self, real, imag=0.0):
        if isinstance(real, str):
            PurePythonComplex.__pyfora_builtins__.raiseInvalidPyforaOperation(
                "Complex initialization from string not implemented"
                )

        if not isinstance(real, float) or not isinstance(imag, float):
            raise TypeError("complex() argument must be a string or a number")

        self.real = float(real)
        self.imag = float(imag)

    def __abs__(self):
        return (self.real * self.real + self.imag * self.imag) ** .5
    
    def conjugate(self):
        return PurePythonComplex(self.real, -self.imag)

    def __mul__(self, other):
        if isinstance(other, PurePythonComplex):
            return PurePythonComplex(
                self.real * other.real - self.imag * other.imag,
                self.real * other.imag + self.imag * other.real
                )
        return PurePythonComplex(self.real * other, self.imag * other)

    def __add__(self, other):
        if isinstance(other, PurePythonComplex):
            return PurePythonComplex(
                self.real + other.real,
                self.imag + other.imag
                )
        return PurePythonComplex(self.real + other, self.imag)

    def __sub__(self, other):
        if isinstance(other, PurePythonComplex):
            return PurePythonComplex(
                self.real - other.real,
                self.imag - other.imag
                )
        return PurePythonComplex(self.real - other, self.imag)

    def __pos__(self):
        return self

    def __neg__(self):
        return PurePythonComplex(-self.real, -self.imag)

    def __nonzero__(self):
        return self.real != 0.0 or self.imag != 0.0

    def __pow__(self, other):
        PurePythonComplex.__pyfora_builtins__.raiseInvalidPyforaOperation(
            "__pow__ not yet implemented on complex"
            )

    def __float__(self):
        raise TypeError("can't convert complex to float")

    def __long__(self):
        raise TypeError("can't convert complex to long")

    def __gt__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __ge__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __lt__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __le__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __eq__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __ne__(self, other):
        raise TypeError("no ordering relation is defined for complex numbers")

    def __str__(self):
        if self.real == 0.0:
            return str(self.imag) + "j"
        return ("(" + str(self.real) + 
            ("+" + str(self.imag) if self.imag > 0 else "-" + str(-self.imag)) + 
            "j)")

    def __sizeof__(self):
        return 32

    def __setattr__(self, val):
        PurePythonComplex.__pyfora_builtins__.raiseInvalidPyforaOperation(
            "__setattr__ not valid in pure python"
            )

    def __mod__(self, other):
        if isinstance(other, PurePythonComplex):
            return PurePythonComplex(self.real % other.real, self.imag % other.imag)
        else:
            return PurePythonComplex(self.real % other, self.imag)

class PurePythonComplexCls(object):
    def __call__(self, real, imag=0.0):
        return PurePythonComplex(real, imag)


class PurePythonComplexMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [complex]

    def getMappableInstances(self):
        return []
        
    def getPurePythonTypes(self):
        return [PurePythonComplex]

    def mapPythonInstanceToPyforaInstance(self, c):
        return PurePythonComplex(c.real, c.imag)

    def mapPyforaInstanceToPythonInstance(self, pureComplex):
        return complex(pureComplex.real, pureComplex.imag)        

def generateMappings():
    return [
        PurePythonComplexMapping(),
        PureImplementationMapping.InstanceMapping(complex, PurePythonComplexCls)
        ]
