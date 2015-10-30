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

import pyfora.PyObjectNodes as PyObjectNodes
import pyfora.PureImplementationMapping as PureImplementationMapping


import numpy as np

class PurePythonNumpyArray:
    def __init__(self, dtype, shape, flat):
        self.dtype = dtype
        self.shape = shape
        self.flat = flat

    def transpose(self):
        newVals = []
        for f in reversed(self.flat):
            newVals = newVals + [f]

        return PurePythonNumpyArray(
            "float64",
            self.shape,
            newVals
            )

    def __len__(self):
        return self.shape[0]

    def __getitem__(self, ix):
        N = self.shape[0]
        M = self.shape[1]
        i = M * ix
        toReturn = []
        for idx in range(i, i + M):
          toReturn = toReturn + [self.flat[idx]]
        return toReturn

    def __mul__(self, v):
        def op(x, y):
            return x * y
        return self.__applyOperatorToAllElements(op, v)

    def __add__(self, v):
        def op(x, y):
            return x + y
        return self.__applyOperatorToAllElements(op, v)

    def __sub__(self, v):
        def op(x, y):
            return x - y
        return self.__applyOperatorToAllElements(op, v)

    def __pow__(self, v):
        def op(x, y):
            return x ** y
        return self.__applyOperatorToAllElements(op, v)

    def __applyOperatorToAllElements(self, op, val):
        toReturn = []
        for v1 in self.flat:
            toReturn = toReturn + [op(v1, val)]

        return PurePythonNumpyArray(
            "float64",
            self.shape,
            toReturn
            )

    def __elementCount(self):
        return reduce(lambda x, y: x * y, self.shape)

    def reshape(self, newShape):
        currentElementCount = self.__elementCount()
        newElementCount = reduce(lambda x, y: x * y, newShape)
        if currentElementCount != newElementCount:
            raise ValueError("Total size of new array must be unchanged")
        return PurePythonNumpyArray(
            "float64",
            newShape,
            self.flat
            )

    def __div__(self, q):
        def op(x, y):
            return x / y
        return self.__applyOperatorToAllElements(op, q)

class PurePythonNumpyArrayMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [np.ndarray]

    def getMappableInstances(self):
        return []
        
    def getPurePythonTypes(self):
        return [PurePythonNumpyArray]

    def mapPythonInstanceToPyforaInstance(self, numpyArray):
        return PurePythonNumpyArray(
            numpyArray.dtype.str,
            numpyArray.shape,
            numpyArray.flatten().tolist()
            )

    def mapPyforaInstanceToPythonInstance(self, pureNumpyArray):
        """Given the converted members of the pyfora object as a dict, return an instance of the mappable type."""
        array = np.fromiter(pureNumpyArray.flat, pureNumpyArray.dtype)
        array.shape = pureNumpyArray.shape
        return array

