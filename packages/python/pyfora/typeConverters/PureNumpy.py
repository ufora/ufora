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
import numpy as np


class PurePythonNumpyArray:
    """
    This is this pyfora wrapper and implementation of the numpy array class
    Internally, the array is stored as a list of values and a tuple of the array dimensions
    """
    def __init__(self, shape, values):
        self.shape = shape
        self.values = values

    def transpose(self):
        if len(self.shape) == 1:
            return self

        newVals = []

        d1 = self.shape[0]
        d2 = self.shape[1]

        newVals = [self[ix1][ix2] for ix2 in xrange(d2) for ix1 in xrange(d1)]

        newShape = tuple(reversed((self.shape)))

        return PurePythonNumpyArray(
            newShape,
            newVals
            )

    def __iter__(self):
        for idx in range(len(self)):
            yield self[idx]

    @property
    def size(self):
        return len(self.values)

    @property
    def ndim(self):
        return len(self.shape)

    def flatten(self):
        """Returns a 1-d numpy array"""
        return PurePythonNumpyArray((self.size,), self.values)

    def tolist(self):
        """Converts an n-dimensional numpy array to an n-dimensional list of lists"""
        def walk(array):
            if not isinstance(array, PurePythonNumpyArray):
                return array
            toReturn = []
            for val in array:
                toReturn = toReturn + [walk(val)]

            return toReturn

        return walk(self)

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
        for idx in range(1, len(self.shape)):
            stride = stride * self.shape[idx]
        toReturn = []
        startIdx = ix * stride
        for idx in range(startIdx, startIdx + stride):
            toReturn = toReturn + [self.values[idx]]

        return PurePythonNumpyArray(newShape, toReturn)

    def __mul__(self, v):
        def op(x, y):
            return x * y
        return self._applyOperatorToAllElements(op, v)

    def __add__(self, v):
        if isinstance(v, PurePythonNumpyArray):
            return self._addArray(v)

        def op(x, y):
            return x + y
        return self._applyOperatorToAllElements(op, v)

    def __sub__(self, v):
        def op(x, y):
            return x - y
        return self._applyOperatorToAllElements(op, v)

    def __pow__(self, v):
        def op(x, y):
            return x ** y
        return self._applyOperatorToAllElements(op, v)

    def __div__(self, q):
        def op(x, y):
            return x / y
        return self._applyOperatorToAllElements(op, q)

    def _addArray(self, v):
        if self.shape != v.shape:
            raise ValueError(
                "operands cannot be added with shapes " + str(self.shape) + \
                " and " + str(v.shape)
                )

        return PurePythonNumpyArray(
            self.shape,
            [self.values[ix] + v.values[ix] for ix in xrange(self.size)]
            )

    def _applyOperatorToAllElements(self, op, val):
        return PurePythonNumpyArray(
            self.shape,
            [op(self.values[ix], val) for ix in xrange(self.size)]
            )

    def reshape(self, newShape):
        impliedElementCount = reduce(lambda x, y: x * y, newShape)
        if self.size != impliedElementCount:
            raise ValueError("Total size of new array must be unchanged")

        return PurePythonNumpyArray(
            newShape,
            self.values
            )


class PurePythonNumpyArrayMapping(PureImplementationMapping.PureImplementationMapping):
    def getMappablePythonTypes(self):
        return [np.ndarray]

    def getMappableInstances(self):
        return []

    def getPurePythonTypes(self):
        return [PurePythonNumpyArray]

    def mapPythonInstanceToPyforaInstance(self, numpyArray):
        return PurePythonNumpyArray(
            numpyArray.shape,
            numpyArray.flatten().tolist()
            )

    def mapPyforaInstanceToPythonInstance(self, pureNumpyArray):
        array = np.array(pureNumpyArray.values)
        array.shape = pureNumpyArray.shape
        return array


class NpZeros:
    def __call__(self, length):
        vals = []
        for _ in range(length):
            vals = vals + [0.0]

        return PurePythonNumpyArray(
            (length,),
            vals
            )


class NpArray:
    """This will only work for a well-formed (not jagged) n-dimensional python lists"""
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
            shape,
            flat
            )


class NpDot:
    def dotProduct(self, arr1, arr2):
        len1 = len(arr1)

        if len1 != len(arr2):
            raise ValueError("Vector dimensions do not match")

        return sum(arr1[ix] * arr2[ix] for ix in xrange(len1))

    def __call__(self, arr1, arr2):
        if isinstance(arr1, PurePythonNumpyArray):
            # The numpy API allows us to multiply a 1D array by a 2D array
            # and numpy will automatically reshape the 1D array to 2D
            if len(arr1.shape) == 1 and len(arr2.shape) == 2:
                arr1 = arr1.reshape((arr1.shape[0], 1,)).transpose()
                return self(arr1, arr2)[0]

            if len(arr1.shape) != len(arr2.shape):
                raise ValueError("Matrix dimensions do not match")

            # 1d dot 1d -> normal dot product
            if len(arr1.shape) == 1:
                return self.dotProduct(arr1, arr2)

            # 2d x 2d -> matrix multiplication
            elif len(arr1.shape) == 2:
                if arr1.shape[1] != arr2.shape[0]:
                    raise ValueError(
                        "shapes " + str(arr1.shape) + " and " + \
                        str(arr2.shape) + " are not aligned: " + \
                        str(arr1.shape[1]) + " (dim 1) != " + \
                        str(arr2.shape[0]) + " (dim 0)"
                        )

                builtins = NpDot.__pyfora_builtins__
                result = builtins.matrixMult(
                    arr1.values, arr1.shape, arr2.values, arr2.shape
                    )
                flattenedValues = result[0]
                shape = tuple(result[1])

                return PurePythonNumpyArray(
                    shape,
                    flattenedValues
                    )

            else:
                raise Exception(
                    "not currently implemented for > 2 dimensions"
                    )

        else:
            return self(np.array(arr1), np.array(arr2))


class NpPinv:
    def __call__(self, matrix):
        builtins = NpPinv.__pyfora_builtins__
        result = builtins.pInv(matrix.values, matrix.shape)
        flat = result[0]
        shape = tuple(result[1])
        return PurePythonNumpyArray(
            shape,
            flat
            )

def generateMappings():
    mappings_ = [(np.zeros, NpZeros), (np.array, NpArray),
                 (np.dot, NpDot), (np.linalg.pinv, NpPinv)]

    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
            (instance, pureType) in mappings_]
    tr.append(PurePythonNumpyArrayMapping())

    return tr


