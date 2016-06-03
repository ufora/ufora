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


from pyfora.PureImplementationMapping import PureImplementationMapping, pureMapping
import pyfora.pure_modules.pure_math as PureMath
from pyfora.pure_modules.pure___builtin__ import Round

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

        if len(self.shape) == 2:
            newVals = []

            d1 = self.shape[0]
            d2 = self.shape[1]

            newVals = [self[ix1][ix2] for ix2 in xrange(d2) for ix1 in xrange(d1)]

            newShape = (d2, d1)

            return PurePythonNumpyArray(
                newShape,
                newVals
                )

        if len(self.shape) == 3:
            newVals = []

            d1 = self.shape[0]
            d2 = self.shape[1]
            d3 = self.shape[2]

            newVals = [self[ix1][ix2][ix3] for ix3 in xrange(d3) for ix2 in xrange(d2) for ix1 in xrange(d1)]

            newShape = (d3, d2, d1)

            return PurePythonNumpyArray(
                newShape,
                newVals
                )

        raise NotImplementedError("Not implemented for dim > 3")

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

        newShape = self.shape[1:]

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
                "operands cannot be zipped with shapes " + str(self.shape) + \
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


@pureMapping
class PurePythonNumpyArrayMapping(PureImplementationMapping):
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


@pureMapping(np.eye)
class NpEye(object):
    def __call__(self, N, M=None):
        if M is None:
            M = N

        vals = [1.0 if colIx == rowIx else 0.0 for rowIx in xrange(N) \
             for colIx in xrange(M)]

        return  PurePythonNumpyArray(
            (N, M),
            vals
            )


@pureMapping(np.zeros)
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


@pureMapping(np.array)
class NpArray(object):
    """This will only work for a well-formed (not jagged) n-dimensional python lists"""
    def __call__(self, array):
        if isinstance(array, PurePythonNumpyArray):
            return array

        if len(array) == 0:
            return PurePythonNumpyArray(
                (0,),
                []
                )

        if not isinstance(array[0], list):
            return PurePythonNumpyArray(
                (len(array),),
                array
                )

        if not isinstance(array[0][0], list):
            return PurePythonNumpyArray(
                (len(array),len(array[0])),
                sum(array, [])
                )

        if not isinstance(array[0][0][0], list):
            return PurePythonNumpyArray(
                (len(array),len(array[0]),len(array[0][0])),
                sum(sum(array, []), [])
                )


        if not isinstance(array[0][0][0][0], list):
            return PurePythonNumpyArray(
                (len(array),len(array[0]),len(array[0][0]), len(array[0][0][0])),
                sum(sum(sum(array, []), []), [])
                )

        raise NotImplementedError("Not implemented for > 4D arrays")

def _dotProduct(arr1, arr2):
    len1 = len(arr1)
    if len1 != len(arr2):
        raise ValueError("Vector dimensions do not match: " + \
                         str(len1) + " vs " + str(len(arr2)))
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
            # right now, values is stored in a row-major fashion
            arr1_flat = arr1.values
            arr2_flat = arr2.values
            res = []
            arr1_flat_ix = 0
            while arr1_flat_ix < len(arr1_flat):
                arr2_flat_ix = 0
                dot = 0.0
                while arr2_flat_ix < len(arr2_flat):
                    dot = dot + arr1_flat[arr1_flat_ix] * arr2_flat[arr2_flat_ix]
                    arr2_flat_ix = arr2_flat_ix + 1
                    arr1_flat_ix = arr1_flat_ix + 1
                res = res + [dot] 

            return PurePythonNumpyArray(
                values=res,
                shape=(len(res),)
                )

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
                """fun(@unnamed_args:(values1, shape1, values2, shape2), *args) {
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


@pureMapping(np.dot)
class NpDot(object):
    def __call__(self, a, b):
        return _dot(a, b)


@pureMapping(np.linalg.pinv)
class NpPinv(object):
    def __call__(self, matrix):
        shape = matrix.shape
        assert len(shape) == 2

        result = __inline_fora(
            """fun(@unnamed_args:(rowMajorValues, shape), *args) {
                   purePython.linalgModule.pInv(rowMajorValues, shape)
                   }"""
            )(matrix.values, shape)

        flat = result[0]
        shape = result[1]
        return PurePythonNumpyArray(
            shape,
            flat
            )


@pureMapping(np.linalg.inv)
class NpInv(object):
    def __call__(self, x):
        shape = x.shape
        assert len(shape) == 2

        # linalgModule throws a TypeError if x is singular
        # we should really be throwing a numpy.linalg.LinAlgError
        result = __inline_fora(
            """fun(@unnamed_args:(rowMajorValues, shape), *args) {
                   purePython.linalgModule.inv(rowMajorValues, shape)
                   }"""
            )(x.values, shape)

        flat = result[0]
        shape = result[1]
        
        return PurePythonNumpyArray(
            shape,
            flat
            )


@pureMapping(np.linalg.eigh)
class NpEigH(object):
    def __call__(self, a, UPLO='L'):
        assert len(a.shape) == 2, "need len(a.shape) == 2"

        res = __inline_fora(
            """fun(@unnamed_args:(a, uplo), *args) {
                   return purePython.linalgModule.eigh(a, uplo)
                   }"""
            )(a, UPLO)

        return (
            PurePythonNumpyArray(
                (a.shape[0],),
                res[1]
                ),
            PurePythonNumpyArray(
                a.shape,
                res[0]
                )
            )
        


@pureMapping(np.linalg.svd)
class Svd(object):
    def __call__(self, a):
        assert len(a.shape) == 2, "need len(a.shape) == 2"

        res = __inline_fora(
            """fun(@unnamed_args:(a), *args) {
                   purePython.linalgModule.svd(a)
                   }"""
            )(a)

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


@pureMapping(np.linalg.lstsq)
class Lstsq(object):
    def __call__(self, a, b, rcond=-1):
        assert len(a.shape) == 2, "need len(a.shape) == 2"
        assert len(b.shape) == 1, "need len(b.shape) == 1"
        assert b.shape[0] == a.shape[0]

        x, singular_values, rank = __inline_fora(
            """fun(@unnamed_args:(a, b, rcond), *args) {
                   purePython.linalgModule.lstsq(a, b, rcond)
                   }"""
            )(a, b, rcond)

        x = PurePythonNumpyArray((len(x),), x)

        if rank < a.shape[1] or a.shape[0] < a.shape[1]:
            residuals = np.array([])
        else:
            residuals = np.array([NpNorm()(NpDot()(a, x) - b) ** 2.0])
        
        return x, residuals, rank, PurePythonNumpyArray(
            (len(singular_values),),
            singular_values)


@pureMapping(np.linalg.norm)
class NpNorm(object):
    def __call__(self, a, ord=None):
        if isinstance(a, list):
            a = np.array(a)

        if len(a.shape) > 2:
            raise ValueError("input array must be 1-d or 2-d")
        
        if ord is None or ord == 'fro':
            return self.frobenius_norm(a)
        elif ord == 'nuc':
            return self.nuclear_norm(a)
        elif ord == np.inf:
            return self.inf_norm(a)
        elif ord == -np.inf:
            return self.minus_inf_norm(a)
        elif ord == 0:
            return self.zero_norm(a)
        elif ord == 1:
            return self.one_norm(a)
        elif ord == -1:
            return self.minus_one_norm(a)
        elif ord == 2:
            return self.two_norm(a)
        elif ord == -2:
            return self.minus_two_norm(a)
        else:
            return sum(abs(elt)**ord for elt in a.values) ** (1.0 / ord)
        
    def frobenius_norm(self, a):
        return sum(elt ** 2.0 for elt in a.values) ** 0.5

    def nuclear_norm(self, a):
        # return sum of singular values
        raise NotImplementedError

    def inf_norm(self, a):
        if len(a.shape) == 1:
            return max(abs(elt) for elt in a.values)
        elif len(a.shape) == 2:
            # max(sum(abs(x), axis=1))
            raise NotImplementedError

        assert False, "shouldn't get here"

    def minus_inf_norm(self, a):
        if len(a.shape) == 1:
            return min(abs(elt) for elt in a.values)
        elif len(a.shape) == 2:
            # min(sum(abs(x), axis=1))
            raise NotImplementedError

        assert False, "shouldn't get here"

    def zero_norm(self, a):
        raise NotImplementedError

    def one_norm(self, a):
        if len(a.shape) == 1:
            return sum(abs(elt) for elt in a.values)
        elif len(a.shape) == 2:
            raise NotImplementedError

        assert False, "shouldn't get here"

    def minus_one_norm(self, a):
        raise NotImplementedError

    def two_norm(self, a):
        if len(a.shape) == 1:
            return self.frobenius_norm(a)
        elif len(a.shape) == 2:
            # 2-norm (largest sing. value)
            raise NotImplementedError

        assert False, "shouldn't get here"

    def minus_two_norm(self, a):
        raise NotImplementedError


@pureMapping(np.linalg.solve)
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
        res = __inline_fora(
            """fun(@unnamed_args:(a,b), *args) {
                   purePython.linalgModule.linsolve(a, b)
                   }"""
            )(a, b)
        flattendValues = res[0]
        shape = res[1]
        return PurePythonNumpyArray(
            shape,
            flattendValues
            )


@pureMapping(np.arange)
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


@pureMapping(np.mean)
class Mean(object):
    def __call__(self, x):
        return sum(x) / len(x)


class Median(object):
    def __call__(self, x):
        raise NotImplementedError("fill this out, bro")


@pureMapping(np.sign)
class Sign(object):
    def __call__(self, x):
        if x < 0.0:
            return -1.0
        elif x == 0.0:
            return 0.0
        return 1.0


@pureMapping(np.isnan)
class IsNan(object):
    def __call__(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(PyFloat(...) x), *args) {
                   PyBool(x.@m.isNan)
                   }"""
            )(x)


@pureMapping(np.isinf)
class IsInf(object):
    def __call__(self, x):
        try:
            return self.isinf_float(x)
        except:
            pass
        try:
            return self.isinf_array(x)
        except:
            raise TypeError(
                "argument could not be coerced to float or array"
                )

    def isinf_float(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(PyFloat(...) x), *args) {
                   PyBool(x.@m.isInfinite)
                   }"""
            )(x)

    def isinf_array(self, x):
        x_asarray = np.array(x)
        
        return PurePythonNumpyArray(
            x_asarray.shape,
            [self.isinf_float(val) for val in x_asarray.values]
            )


@pureMapping(np.isfinite)
class IsFinite(object):
    def __call__(self, x):
        if isinstance(x, list):
            return self.isfinite_array(x)

        if isinstance(x, PurePythonNumpyArray):
            return self.isfinite_array(x)
        
        try:
            return self.isfinite_float(x)
        except:
            pass

        try:
            return self.isfinite_array(x)
        except:
            raise TypeError(
                "argument could not be coerced to float or array"
                )

    def isfinite_float(self, x):
        if not isinstance(x, float):
            x = float(x)

        return __inline_fora(
            """fun(@unnamed_args:(PyFloat(...) x), *args) {
                   PyBool(x.@m.isFinite)
                   }"""
            )(x)

    def isfinite_array(self, x):
        x_asarray = np.array(x)
        
        return PurePythonNumpyArray(
            x_asarray.shape,
            [self.isfinite_float(val) for val in x_asarray.values]
            )


@pureMapping(np.abs)
class NpAbs(object):
    def __call__(self, x):
        try:
            return self.abs_primitive(x)
        except:
            pass
        try:
            return self.abs_array(x)
        except:
            raise TypeError(
                "argument " + str(x) + " could not be coerced to bool or array"
                )

    def abs_primitive(self, x):
        # this next call might raise an exception, but that's ok
        x_as_float = float(x)

        return abs(x_as_float)

    def abs_array(self, x):
        x_asarray = np.array(x)
        
        return PurePythonNumpyArray(
            x_asarray.shape,
            [self.abs_primitive(val) for val in x_asarray.values]
            )


@pureMapping(np.all)
class All(object):
    def __call__(self, x):
        if isinstance(x, list) or isinstance(x, PurePythonNumpyArray):
            return self.all_array(x)
        
        try:
            return self.all_primitive(x)
        except:
            pass

        try:
            return self.all_array(x)
        except:
            raise TypeError(
                "argument " + str(x) + " could not be coerced to bool or array"
                )

    def all_primitive(self, x):
        # this next call might raise an exception, but that's ok
        x_as_float = float(x)

        return bool(x_as_float)

    def all_array(self, x):
        x_asarray = np.array(x)
        
        return all([self.all_primitive(val) for val in x_asarray.values])


@pureMapping(np.log)
class Log(object):
    def __call__(self, val):
        if val < 0:
            return np.nan

        if val == 0:
            return -np.inf

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.log(val.@m))
                   }"""
            )(val)


@pureMapping(np.log10)
class Log10(object):
    def __call__(self, val):
        if val < 0:
            return np.nan

        if val == 0:
            return -np.inf

        return __inline_fora(
            """fun(@unnamed_args:(val), *args) {
                   PyFloat(math.log_10(val.@m))
                   }"""
            )(val)


@pureMapping(np.log1p)
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


@pureMapping(np.sqrt)
class Sqrt(object):
    def __call__(self, val):
        if val < 0.0:
            return np.nan

        return val ** 0.5


@pureMapping(np.round)
class NpRound(object):
    def __call__(self, x):
        return Round()(x)


@pureMapping(np.cos)
class NpCos(object):
    def __call__(self, x):
        return PureMath.Cos()(x)


@pureMapping(np.sin)
class NpSin(object):
    def __call__(self, x):
        return PureMath.Sin()(x)


@pureMapping(np.tan)
class NpTan(object):
    def __call__(self, x):
        return PureMath.Tan()(x)


@pureMapping(np.hypot)
class NpHypot(object):
    def __call__(self, x):
        return PureMath.Hypot()(x)


@pureMapping(np.exp)
class NpExp(object):
    def __call__(self, x):
        return PureMath.Exp()(x)


@pureMapping(np.expm1)
class NpExpm1(object):
    def  __call__(self, x):
        return PureMath.Expm1()(x)


@pureMapping(np.floor)
class NpFloor(object):
    def __call__(self, x):
        return PureMath.Floor()(x)


@pureMapping(np.random.mtrand.RandomState, module='numpy')
class NumpyRandomMtrandRandomState(object):
    def __call__(self, seed):
        return RandomState(seed)


class RandomState(object):
    def __init__(self, seed=None):
        assert seed is not None, "must pass in a seed"

        self.savedNormalPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(Float64).create(1, 0.0)
                   }"""
            )()
        
        self.hasSavedNormalPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(Bool).create(1, false)
                   }"""
            )()
        
        self.indexPtr = __inline_fora(
            """fun(*args) {
                   MutableVector(UInt32).create(1, 624u32)
                   }"""
            )()
        self.stateVector = __inline_fora(
            """fun(@unnamed_args:(seed), *args) {
                   seed = UInt32(seed.@m)
                   if (seed < 0)
                       throw ValueError(PyString("seeds must be non-negative"))

                   let stateVector = MutableVector(UInt32).create(624, 0u32);
                   stateVector[0] = seed;

                   let ix = 0u32;
                   while (ix < 623u32) {
                       seed = 1812433253u32 * (stateVector[ix] ^ (stateVector[ix] >> 30u32)) + ix + 1u32;
                       ix = ix + 1u32
                       stateVector[ix] = seed
                       }

                   return stateVector
                   }"""
            )(seed)


    def pull_int_(self):
        return __inline_fora(
            """fun(@unnamed_args:(indexPtr, stateVector), *args) {
                   let twist = fun() {
                       let lookup = fun(ix) {
                           if (ix < 624u32)
                               return stateVector[ix]

                           return stateVector[ix - 624u32]
                           }

                       let ix = 0u32;
                       while (ix < 624u32) {
                           let xL = lookup(ix + 1) & 2147483647u32
                           let xU = stateVector[ix] & 2147483648u32
                           let y = (xL | xU);

                           if (y % 2u32 == 1u32)
                               y = (y >> 1u32) ^ 2567483615u32
                           else
                               y = (y >> 1u32)


                           stateVector[ix] = lookup(ix + 397u32) ^ y

                           ix = ix + 1u32
                           }

                       indexPtr[0] = 0u32
                       stateVector
                       }

                   if (indexPtr[0] >= 624u32)
                       twist() // modifies indexPtr

                   let index = indexPtr[0]
                   let y = stateVector[index]

                   y = y ^ (y >> 11u32);
                   y = y ^ ((y << 7u32) & 2636928640u32);
                   y = y ^ ((y << 15u32) & 4022730752u32);
                   y = y ^ (y >> 18u32);

                   indexPtr[0] = index + 1u32

                   return PyInt(y);
                   }"""
            )(self.indexPtr, self.stateVector)
        
    def pull_uniform_(self, low=0.0, high=1.0):
        i0 = self.pull_int_()
        i1 = self.pull_int_()
        a, b = __inline_fora(
            """fun(@unnamed_args:(i0, i1), *args) {
                   let a = PyInt(i0.@m >> 5);
                   let b = PyInt(i1.@m >> 6);
                   return PyTuple((a, b))
                   }"""
            )(i0, i1)

        return low + (high - low) * (a * 67108864.0 + b) / 9007199254740992.0

    def pull_normal_(self):
        if __inline_fora(
                """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                       PyBool(hasSavedNormalPtr[0])
                       }"""
                )(self.hasSavedNormalPtr):
            tr = __inline_fora(
                """fun(@unnamed_args:(savedNormalPtr), *args) {
                       PyFloat(savedNormalPtr[0])
                       }"""
                )(self.savedNormalPtr)
            __inline_fora(
                """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                       hasSavedNormalPtr[0] = false
                       }"""
                )(self.hasSavedNormalPtr)
            return tr
        
        normal0, normal1 = self.pull_two_normals_()

        __inline_fora(
            """fun(@unnamed_args:(normalToSave, savedNormalPtr), *args) {
                   savedNormalPtr[0] = normalToSave.@m
                   }"""
            )(normal0, self.savedNormalPtr)

        __inline_fora(
            """fun(@unnamed_args:(hasSavedNormalPtr), *args) {
                   hasSavedNormalPtr[0] = true
                   }"""
            )(self.hasSavedNormalPtr)

        return normal1

    def pull_two_normals_(self):
        tryIx = 0
        while tryIx < 1000000:
            u = self.pull_uniform_(-1.0, 1.0)
            v = self.pull_uniform_(-1.0, 1.0)
            s = u * u + v * v
            if s <= 1.0 and s != 0.0:
                f = (-2.0 * math.log(s) / s) ** 0.5
                return u * f, v * f

            tryIx = tryIx + 1
                
        assert False, "too many tries in pull_two_normals_"            

    def rand(self, size=None):
        if size is None:
            return self.pull_uniform_()

        tr = []
        for _ in xrange(size):
            tr = tr + [self.pull_uniform_()]

        return np.array(tr)

    def randn(self, size=None):
        if size is None:
            return self.pull_normal_()

        tr = []
        ix = 0
        while ix < size:
            tr = tr + [self.pull_normal_()]
            ix = ix + 1

        return np.array(tr)

    def uniform(self, low=0.0, high=1.0, size=None):
        if size is None:
            return self.pull_uniform_(low=low, high=high)

        tr = []
        ix = 0
        while ix < size:
            tr = tr + [self.pull_uniform_(low=low, high=high)]
            ix = ix + 1

        return np.array(tr)

