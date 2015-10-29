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
import pyfora.BuiltinPureImplementationMappings as BuiltinPureImplementationMappings

class PurePythonNumpyArray:
    """
    This is this pyfora wrapper and implementation of the numpy array class
    Internally, the array is stored as a list of values and a tuple of the array dimensions
    """
    def __init__(self, dtype, shape, values):
        self.dtype = dtype
        self.shape = shape
        self.values = values

    def transpose(self):
        if len(self.shape) == 1:
            return self

        newVals = []

        d1 = self.shape[0]
        d2 = self.shape[1]

        for ix2 in range(d2):
            for ix1 in range(d1):
                newVals = newVals + [self[ix1][ix2]]

        newShape = BuiltinPureImplementationMappings.Reversed()(self.shape)
        newShape = tuple(newShape)

        return PurePythonNumpyArray(
            "float64",
            newShape,
            newVals
            )

    def __len__(self):
        return self.shape[0]

    def __getitem__(self, ix):
        if len(self.shape) == 1:
            return self.values[ix]

        def shapeOfResultantArray(originalShape):
            newShape = []
            for idx in range(len(originalShape)):
                if idx != 0:
                    newShape = newShape + [originalShape[idx]]
            return newShape

        newShape = shapeOfResultantArray(self.shape)
        stride = 1
        for ix in range(1, len(self.shape)):
            stride = stride * self.shape[ix]
        toReturn = []
        startIdx = ix * stride
        for idx in range(startIdx, startIdx + stride):
            toReturn = toReturn + [self.values[idx]]

        return PurePythonNumpyArray(self.dtype, newShape, toReturn)

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
        for v1 in self.values:
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
            self.values
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
        array = np.fromiter(pureNumpyArray.values, pureNumpyArray.dtype)
        array.shape = pureNumpyArray.shape
        return array

class NpZeros:
    def __call__(self, length):
        vals = []
        for _ in range(length):
            vals = vals + [0.0]
        
        return PurePythonNumpyArray(
            "float64",
            (length,),
            vals
            )

class NpArray:
    """This will only work for a well-formed (not jagged) two dimensional python lists"""
    def __call__(self, array):
        def flattenAnNDimensionalArray(arr, shape):
            toReturn = []
            if len(shape) == 0:
                return arr
            else:
                newShape = []
                for idx in range(len(shape)):
                    if idx != 0:
                        newShape = newShape + [shape[idx]]

                for subArr in arr:
                    v = flattenAnNDimensionalArray(subArr, newShape)
                    if not isinstance(v, list):
                        toReturn = toReturn + [v]
                    else:
                        for v2 in v:
                            toReturn = toReturn + [v2]
                return toReturn

        shape = []
        inspection = array
        while isinstance(inspection, list):
            shape = shape + [len(inspection)]
            inspection = inspection[0]

        flat = flattenAnNDimensionalArray(array, shape)
        shape = tuple(shape)
        return PurePythonNumpyArray(
            "float64",
            shape,
            flat
            )

class NpDot:
    def __call__(self, arr1, arr2):
        l1 = len(arr1)
        l2 = len(arr2)
        if l1 != l2:
            raise ValueError("Vector dimensions do not match")
        toReturn = 0
        for idx in range(l1):
            toReturn = toReturn + arr1[idx] * arr2[idx]
        return toReturn

mappings_ = [(np.zeros, NpZeros), (np.array, NpArray), (np.dot, NpDot)]

def generateMappings():
    return [PureImplementationMapping.InstanceMapping(instance, pureType) for (instance, pureType) in mappings_]
