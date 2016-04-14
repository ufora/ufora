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


"""Pure Python Implementations of Python builtins (in alphabetical order)."""

import math
import pyfora.PureImplementationMapping as PureImplementationMapping
from pyfora.PureImplementationMapping import pureMapping


# List of Python 2.7 builtins:
# 'abs', 'all', 'any', 'apply', 'basestring', 'bin', 'bool', 'buffer', 'bytearray',
# 'bytes', 'callable', 'chr', 'classmethod', 'cmp', 'coerce', 'compile', 'complex',
# 'copyright', 'credits', 'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval',
# 'execfile', 'exit', 'file', 'filter', 'float', 'format', 'frozenset', 'getattr',
# 'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'intern',
# 'isinstance', 'issubclass', 'iter', 'len', 'license', 'list', 'locals', 'long',
# 'map', 'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
# 'print', 'property', 'quit', 'range', 'raw_input', 'reduce', 'reload', 'repr',
# 'reversed', 'round', 'set', 'setattr', 'slice', 'sorted', 'staticmethod', 'str',
# 'sum', 'super', 'tuple', 'type', 'unichr', 'unicode', 'vars', 'xrange', 'zip'


@pureMapping(abs)
class Abs(object):
    def __call__(self, val):
        return val.__abs__()


@pureMapping(all)
class All(object):
    def __call__(self, iterable):
        if len(iterable) == 0:
            return True
        for i in iterable:
            if not i:
                return False
        return True


@pureMapping(any)
class Any(object):
    def __call__(self, iterable):
        if len(iterable) == 0:
            return False
        for i in iterable:
            if i:
                return True
        return False


@pureMapping(chr)
class Chr(object):
    def __call__(self, asciiValue):
        return asciiValue.__pyfora_chr__()


@pureMapping(enumerate)
class Enumerate(object):
    def __call__(self, iterable):
        count = 0
        for val in iterable:
            yield (count, val)
            count = count + 1


@pureMapping(len)
class Len(object):
    def __call__(self, other):
        return other.__len__()


@pureMapping(max)
class Max(object):
    def __call__(self, a, b=None):
        if b is not None:
            if a < b:
                return b
            return a
        else:
            a = list(a)

            if len(a) == 0:
                raise ValueError("arg is an empty sequence")
                
            tr = a[0]

            ix = 1
            while ix < len(a):
                val = a[ix]
                if val > tr:
                    tr = val
                ix = ix + 1
                
            return tr


@pureMapping(min)
class Min(object):
    def __call__(self, a, b=None):
        if b is not None:
            if a < b:
                return a
            return b
        else:
            a = list(a)

            if len(a) == 0:
                raise ValueError("arg is an empty sequence")
                
            tr = a[0]

            ix = 1
            while ix < len(a):
                val = a[ix]
                if val < tr:
                    tr = val
                ix = ix + 1
                
            return tr
            

@pureMapping(ord)
class Ord(object):
    def __call__(self, character):
        # assert we're getting a character of length 1
        if len(character) != 1:
            raise TypeError("ord() expected a character")

        return __inline_fora(
            """fun(@unnamed_args:(s), *args) { PyInt(Int64(s.@m[0])) }"""
            )(character)


@pureMapping(range)
class Range(object):
    def __call__(self, first, second=None, increment=None):
        return list(xrange(first, second, increment))



class Empty(object):
    pass

@pureMapping(reduce)
class Reduce(object):
    def __call__(self, f, sequence, start=Empty):
        #get a generator
        generator = sequence.__pyfora_generator__()

        if not generator.canSplit():
            result = start
            for val in generator:
                if result is Empty:
                    result = val
                else:
                    result = f(result, val)
            return result
        else:
            def sum_(sumSubGenerator, depth):
                if depth > 9 or not sumSubGenerator.canSplit():
                    result = Empty

                    if sumSubGenerator.isNestedGenerator():
                        #the outer generator might not be splittable anymore, but
                        #the inner ones might
                        for childGenerator in sumSubGenerator.childGenerators():
                            if result is Empty:
                                result = sum_(childGenerator, depth+1)
                            else:
                                result = f(result, sum_(childGenerator, depth+1))
                    else:
                        for val in sumSubGenerator:
                            if result is Empty:
                                result = val
                            else:
                                result = f(result, val)
                    return result
                else:
                    split = sumSubGenerator.split()
                    left = sum_(split[0], depth+1)
                    right = sum_(split[1], depth+1)

                    if left is Empty:
                        return right
                    if right is Empty:
                        return left
                    return f(left, right)

            result = sum_(generator, 0)

            if result is Empty:
                if start is Empty:
                    raise TypeError("reduce() of empty sequence with no initial value")
                return start

            if start is Empty:
                return result

            return f(start, result)


@pureMapping(map)
class Map(object):
    def __call__(self, f, iterable):
        if f is None:
            f = lambda x:x
        return [f(x) for x in iterable]


@pureMapping(reversed)
class Reversed(object):
    def __call__(self, arr):
        l = len(arr)
        for idx in xrange(l):
            v = arr[l - idx - 1]
            yield v


@pureMapping(sum)
class Sum(object):
    def __call__(self, sequence, start=0):
        return reduce(lambda x,y: x+y, sequence, start)


class XRangeInstance(object):
    def __init__(self, start, count, increment):
        self.start = start
        self.count = count
        self.increment = increment

    def __iter__(self):
        currentVal = self.start
        ix = 0

        while ix < self.count:
            yield currentVal
            currentVal = currentVal + self.increment
            ix = ix + 1


    def __pyfora_generator__(self):
        class Generator:
            def __init__(self, start, count, increment):
                self.start = start
                self.count = count
                self.increment = increment

            def __pyfora_generator__(self):
                return self

            def __iter__(self):
                ix = 0
                currentVal = self.start
                while ix < self.count:
                    yield currentVal
                    currentVal = currentVal + self.increment
                    ix = ix + 1

            def isNestedGenerator(self):
                return False

            def canSplit(self):
                return self.count > 1

            def split(self):
                if self.count <= 1:
                    return None

                lowCount = self.count / 2
                highCount = self.count - lowCount

                return (
                    Generator(self.start, lowCount, self.increment),
                    Generator(self.start + self.increment * lowCount, highCount, self.increment)
                    )

            def map(self, f):
                return __inline_fora(
                    """fun(@unnamed_args:(self, f), *args) {
                           return purePython.MappingGenerator(self, f)
                           }"""
                    )(self, f)

            def filter(self, f):
                return __inline_fora(
                    """fun(@unnamed_args:(self, f), *args) {
                           return purePython.FilteringGenerator(self, f)
                           }"""
                    )(self, f)

            def nest(self, subgeneratorFun):
                return __inline_fora(
                    """fun(@unnamed_args:(self, f), *args) {
                           return purePython.NestedGenerator(self, f)
                           }"""
                    )(self, subgeneratorFun)

            def associativeReduce(self, initValSoFar, add, merge, empty):
                """__without_stacktrace_augmentation"""

                return __inline_fora("""
                    fun(@unnamed_args:(initValSoFar,
                                       start,
                                       increment,
                                       add,
                                       merge,
                                       empty,
                                       count),
                        *args)
                        {
                        __without_stacktrace_augmentation {
                            AssociativeReduce.associativeReduceIntegers(
                                initValSoFar,
                                fun(lst, ix) { 
                                    __without_stacktrace_augmentation {
                                        add(lst, PyInt(start.@m + ix * increment.@m))
                                        }
                                    },
                                merge,
                                empty,
                                0,
                                count.@m
                                )
                            }
                        }
                    """)(initValSoFar, self.start, self.increment, add, merge, empty, self.count)

        return Generator(self.start, self.count, self.increment)


@pureMapping(xrange)
class XRange(object):
    def __call__(self, first, second=None, increment=None):
        if not isinstance(first, int):
            raise TypeError("range() first argument must be an integer")

        start = 0
        stop = 0
        if second is None:
            stop = first
        else:
            if not isinstance(second, int):
                raise TypeError(
                    "range() second argument must be an integer (or None)"
                    )

            start = first
            stop = second

        if increment is None:
            increment = 1
        elif not isinstance(increment, int):
            raise TypeError(
                "range() third argument must be an integer (or None)"
                )

        if increment == 0:
            raise ValueError("xrange() arg 3 must not be zero")

        if increment > 0:
            count = max(0, (stop - start - 1) / increment + 1)
        else:
            count = max(0, (start - stop - 1) / (-increment) + 1 )

        return XRangeInstance(start, count, increment)


@pureMapping(sorted)
class Sorted(object):
    def __call__(self, iterable):
        if isinstance(iterable, list):
            return Sorted._sortList(iterable)
        else:
            return Sorted._sortList([val for val in iterable])

    @staticmethod
    def _sortList(xs):
        return __inline_fora(
            """fun(@unnamed_args:(xs), *args) {
                   return purePython.PyforaBuiltins.sorted(xs)
                   }"""
            )(xs)


@pureMapping(round)
class Round(object):
    def __call__(self, x):
        f = math.floor(x)

        if abs(x - f) < 0.5:
            return f

        return f + 1


@pureMapping
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


@pureMapping(complex)
class PurePythonComplex(object):
    def __init__(self, real, imag=0.0):
        if isinstance(real, str):
            __inline_fora(
                """fun(@unnamed_args:(msg), *args) {
                       purePython.PyforaBuiltins.raiseInvalidPyforaOperation(
                           msg
                           )
                       }"""
                )("Complex initialization from string not implemented")

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
        __inline_fora(
            """fun(@unnamed_args:(msg), *args) {
                       purePython.PyforaBuiltins.raiseInvalidPyforaOperation(
                           msg
                           )
                       }"""
                )("__pow__ not yet implemented on complex")

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
        __inline_fora(
            """fun(@unnamed_args:(msg), *args) {
                       purePython.PyforaBuiltins.raiseInvalidPyforaOperation(
                           msg
                           )
                       }"""
                )("__setattr__ not valid in pure python")

    def __mod__(self, other):
        if isinstance(other, PurePythonComplex):
            return PurePythonComplex(self.real % other.real, self.imag % other.imag)
        else:
            return PurePythonComplex(self.real % other, self.imag)

@pureMapping(complex)
class PurePythonComplexCls:
    def __call__(self, real, imag=0.0):
        return PurePythonComplex(real, imag)

