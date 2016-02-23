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
import pyfora.BuiltinPureImplementationMappings as BuiltinPureImplementationMappings


import math
import numpy as np


class PurePythonNumpyArray(object):
    """
    This is this pyfora wrapper and implementation of the numpy array class
    Internally, the array is stored as a list of values and a tuple of the
    array dimensions. Currently, the values block is interpreted in a
    *row major* fashion.
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
        for idx in xrange(len(self)):
            yield self[idx]

    def __eq__(self, y):
        # true numpy usese some "broadcasting" rules
        # to decide the shape of the resultant array
        # here we're restricting to the simpler case
        # where both arrays have the same size
        if self.shape != y.shape:
            raise ValueError(
                "__eq__ only currently implemented for equal-sized arrays"
                )

        tr = [self.values[ix] == y.values[ix] for ix in xrange(self.size)]
        return PurePythonNumpyArray(self.shape, tr)

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
            if isinstance(ix, slice):
                vals = self.values[ix]
                return PurePythonNumpyArray((len(vals),), vals)
            else:
                return self.values[ix]

        def shapeOfResultantArray(originalShape):
            newShape = []
            for idx in xrange(len(originalShape)):
                if idx != 0:
                    newShape = newShape + [originalShape[idx]]
            return newShape

        newShape = shapeOfResultantArray(self.shape)
        stride = 1
        for idx in xrange(1, len(self.shape)):
            stride = stride * self.shape[idx]
        toReturn = []
        startIdx = ix * stride
        for idx in xrange(startIdx, startIdx + stride):
            toReturn = toReturn + [self.values[idx]]

        return PurePythonNumpyArray(newShape, toReturn)

    def __neg__(self):
        return PurePythonNumpyArray(
            self.shape,
            [-val for val in self.values]
            )

    def __mul__(self, v):
        def op(x, y):
            return x * y

        if isinstance(v, PurePythonNumpyArray):
            return self._zipArraysWithOp(v, op)

        return self._applyOperatorToAllElements(op, v)

    def __add__(self, v):
        def op(x, y):
            return x + y

        if isinstance(v, PurePythonNumpyArray):
            return self._zipArraysWithOp(v, op)

        return self._applyOperatorToAllElements(op, v)

    def __sub__(self, v):
        def op(x, y):
            return x - y

        if isinstance(v, PurePythonNumpyArray):
            return self._zipArraysWithOp(v, op)

        return self._applyOperatorToAllElements(op, v)

    def __pow__(self, v):
        def op(x, y):
            return x ** y

        if isinstance(v, PurePythonNumpyArray):
            return self._zipArraysWithOp(v, op)

        return self._applyOperatorToAllElements(op, v)

    def __div__(self, q):
        def op(x, y):
            return x / y

        if isinstance(q, PurePythonNumpyArray):
            return self._zipArraysWithOp(q, op)

        return self._applyOperatorToAllElements(op, q)

    def _zipArraysWithOp(self, v, op):
        if self.shape != v.shape:
            raise ValueError(
                "operands cannot be added with shapes " + str(self.shape) + \
                " and " + str(v.shape)
                )

        return PurePythonNumpyArray(
            self.shape,
            [op(self.values[ix], v.values[ix]) for ix in xrange(self.size)]
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

    def dot(self, other):
        return _dot(self, other)


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
        try:
            return array.reshape(pureNumpyArray.shape)
        except:
            assert False, (pureNumpyArray.values, pureNumpyArray.shape)


class NpZeros(object):
    def __call__(self, length):
        def zerosFromCountAndShape(count, shape):
            vals = [0.0 for _ in xrange(count)]
            return PurePythonNumpyArray(
                shape,
                vals
                )

        if isinstance(length, tuple):
            # in this case, tuple is the shape of the array
            count = reduce(lambda x, y: x*y, length)
            return zerosFromCountAndShape(count, length)
        else:
            # in this case tuple is the length of the array
            return zerosFromCountAndShape(length, (length,))


class NpArray(object):
    """This will only work for a well-formed (not jagged) n-dimensional python lists"""
    def __call__(self, array):
        if isinstance(array, PurePythonNumpyArray):
            return array

        if not isinstance(array[0], list):
            return PurePythonNumpyArray(
                (len(array),),
                array
                )

        def flattenAnNDimensionalArray(arr, shape):
            toReturn = []
            if len(shape) == 0:
                return arr
            else:
                newShape = []
                for idx in xrange(len(shape)):
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


def _dotProduct(arr1, arr2):
    len1 = len(arr1)

    if len1 != len(arr2):
        raise ValueError("Vector dimensions do not match")

    return sum(arr1[ix] * arr2[ix] for ix in xrange(len1))


def _dot(arr1, arr2):
    if isinstance(arr1, PurePythonNumpyArray) and \
       isinstance(arr2, PurePythonNumpyArray):
        # The numpy API allows us to multiply a 1D array by a 2D array
        # and numpy will automatically reshape the 1D array to 2D
        if len(arr1.shape) == 1 and len(arr2.shape) == 2:
            arr1 = arr1.reshape((1, arr1.shape[0]))
            return _dot(arr1, arr2)[0]

        if len(arr1.shape) == 2 and len(arr2.shape) == 1:
            return _dot(arr2, arr1.transpose())

        if len(arr1.shape) != len(arr2.shape):
            raise ValueError("Matrix dimensions do not match")

        # 1d dot 1d -> normal dot product
        if len(arr1.shape) == 1:
            return _dotProduct(arr1, arr2)

        # 2d x 2d -> matrix multiplication
        elif len(arr1.shape) == 2:
            if arr1.shape[1] != arr2.shape[0]:
                raise ValueError(
                    "shapes " + str(arr1.shape) + " and " + \
                    str(arr2.shape) + " are not aligned: " + \
                    str(arr1.shape[1]) + " (dim 1) != " + \
                    str(arr2.shape[0]) + " (dim 0)"
                    )

            result = __inline_fora(
                """fun(values1, shape1, values2, shape2) {
                       return purePython.linalgModule.matrixMult(
                           values1, shape1, values2, shape2
                           )
                       }"""
                )(arr1.values, arr1.shape, arr2.values, arr2.shape)

            flattenedValues = result[0]
            shape = tuple(result[1])

            return PurePythonNumpyArray(
                shape,
                flattenedValues
                )

        else:
            raise Exception(
                "not currently implemented for > 2 dimensions: "
                )

    else:
        return _dot(NpArray()(arr1), NpArray()(arr2))


class NpDot(object):
    def __call__(self, a, b):
        return _dot(a, b)


class NpPinv(object):
    def __call__(self, matrix):
        builtins = NpPinv.__pyfora_builtins__

        shape = matrix.shape
        assert len(shape) == 2

        result = builtins.linalg.pInv(matrix.values, shape)
        flat = result[0]
        shape = result[1]
        return PurePythonNumpyArray(
            shape,
            flat
            )


class Svd(object):
    def __call__(self, a):
        assert len(a.shape) == 2, "need len(a.shape) == 2"
        
        res = Svd.__pyfora_builtins__.linalg.svd(a)

        return (
            PurePythonNumpyArray(
                res[0][1],
                res[0][0]
                ),
            PurePythonNumpyArray(
                (len(res[1]),),
                res[1]
                ),
            PurePythonNumpyArray(
                res[2][1],
                res[2][0]
                )
            )


class LinSolve(object):
    def __call__(self, a, b):
        assert len(a.shape) == 2, "need len(a.shape) == 2"
        assert a.shape[0] == a.shape[1], "need a.shape[0] == a.shape[1]"
        assert a.shape[0] == b.shape[0], "need a.shape[0] == b.shape[0]"

        if len(b.shape) == 2:
            return self._linsolv_impl(a, b)
        elif len(b.shape) == 1:
            res = self._linsolv_impl(a, b.reshape((len(b),1)))
            return res.reshape((len(res),))

        assert False, "need len(b.shape) == 2 or len(b.shape) == 1"

    def _linsolv_impl(self, a, b):
        res = LinSolve.__pyfora_builtins__.linalg.linsolve(a, b)
        flattendValues = res[0]
        shape = res[1]
        return PurePythonNumpyArray(
            shape,
            flattendValues
            )


class NpArange(object):
    def __call__(self, start, stop=None, step=1):
        if stop is None:
            stop = start
            start = 0 if isinstance(stop, int) else 0.0
        currentVal = start
        toReturn = []
        while currentVal < stop:
            toReturn = toReturn + [currentVal]
            currentVal = currentVal + step
        return NpArray()(toReturn)


class Mean(object):
    def __call__(self, x):
        return sum(x) / len(x)


class Median(object):
    def __call__(self, x):
        raise NotImplementedError("fill this out, bro")


class Sign(object):
    def __call__(self, x):
        if x < 0.0:
            return -1.0
        elif x == 0.0:
            return 0.0
        return 1.0


class IsNan(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(PyFloat(...) x) {
                   PyBool(x.@m.isNan)
                   }"""
            )(x)


class IsInf(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(PyFloat(...) x) {
                   PyBool(x.@m.isInfinite)
                   }"""
            )(x)


class Log(object):
    def __call__(self, val):
        if val < 0:
            return np.nan

        if val == 0:
            return -np.inf

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log(val.@m))
                   }"""
            )(val)


class Log10(object):
    def __call__(self, val):
        if val < 0:
            return np.nan

        if val == 0:
            return -np.inf

        return __inline_fora(
            """fun(val) {
                   PyFloat(math.log_10(val.@m))
                   }"""
            )(val)


class Log1p(object):
    def __call__(self, x):
        if x < -1:
            return np.nan

        if x == -1:
            return -np.inf

        t = float(1.0 + x)
        # if very small, x serves as good approximation
        if t == 1.0:
            return x

        return math.log(t) * (x / (t - 1.0))


class Sqrt(object):
    def __call__(self, val):
        if val < 0.0:
            return np.nan

        return val ** 0.5


def generateMappings():
    mappings_ = [(np.zeros, NpZeros), (np.array, NpArray), (np.dot, NpDot),
                 (np.linalg.pinv, NpPinv), (np.linalg.solve, LinSolve),
                 (np.linalg.svd, Svd),
                 (np.arange, NpArange)]

    # these will need their own implementations in PureNumpy since in true numpy
    # they admit "vectorized" forms
    mappings_ = mappings_ + [
        (np.cos, PureMath.Cos), (np.sin, PureMath.Sin), (np.tan, PureMath.Tan),
        (np.cosh, PureMath.Cosh), (np.sinh, PureMath.Sinh), (np.tanh, PureMath.Tanh),
        (np.sqrt, Sqrt), (np.hypot, PureMath.Hypot), (np.log, Log),
        (np.exp, PureMath.Exp), (np.expm1, PureMath.Expm1), (np.floor, PureMath.Floor),
        (np.isnan, IsNan), (np.sign, Sign), (np.log1p, Log1p),
        (np.isinf, IsInf),
        (np.log10, Log10),
        (np.round, BuiltinPureImplementationMappings.Round)
        ]


    tr = [PureImplementationMapping.InstanceMapping(instance, pureType) for \
            (instance, pureType) in mappings_]

    tr.append(PurePythonNumpyArrayMapping())

    return tr


