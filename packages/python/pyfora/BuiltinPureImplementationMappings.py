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


import pyfora.PureImplementationMapping as PureImplementationMapping


import math


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


class Abs:
    def __call__(self, val):
        return val.__abs__()


class All:
    def __call__(self, iterable):
        if len(iterable) == 0:
            return True
        for i in iterable:
            if not i:
                return False
        return True


class Any:
    def __call__(self, iterable):
        if len(iterable) == 0:
            return False
        for i in iterable:
            if i:
                return True
        return False


class Chr:
    def __call__(self, asciiValue):
        return asciiValue.__pyfora_chr__()

class Enumerate:
    def __call__(self, iterable):
        count = 0
        for val in iterable:
            yield (count, val)
            count = count + 1

class Len:
    def __call__(self, other):
        return other.__len__()


class Max:
    def __call__(self, a, b):
        if a < b:
            return b
        return a


class Min:
    def __call__(self, a, b):
        if a < b:
            return a
        return b


class Ord:
    def __call__(self, character):
        # assert we're getting a character of length 1
        if len(character) != 1:
            raise TypeError("ord() expected a character")

        return character.__pyfora_ord__()


class Range:
    def __call__(self, first, second=None, increment=None):
        return list(xrange(first, second, increment))


class Empty:
    pass


class Reduce:
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
            def sum(sumSubGenerator, depth):
                if depth > 9 or not sumSubGenerator.canSplit():
                    result = Empty

                    if sumSubGenerator.isNestedGenerator():
                        #the outer generator might not be splittable anymore, but
                        #the inner ones might
                        for childGenerator in sumSubGenerator.childGenerators():
                            if result is Empty:
                                result = sum(childGenerator, depth+1)
                            else:
                                result = f(result, sum(childGenerator, depth+1))
                    else:
                        for val in sumSubGenerator:
                            if result is Empty:
                                result = val
                            else:
                                result = f(result, val)
                    return result
                else:
                    split = sumSubGenerator.split()
                    left = sum(split[0], depth+1)
                    right = sum(split[1], depth+1)

                    if left is Empty:
                        return right
                    if right is Empty:
                        return left
                    return f(left, right)

            result = sum(generator, 0)

            if result is Empty:
                if start is Empty:
                    raise TypeError("reduce() of empty sequence with no initial value")
                return start

            if start is Empty:
                return result

            return f(start, result)


class Map:
    def __call__(self, f, iterable):
        if f is None:
            f = lambda x:x
        return [f(x) for x in iterable]


class Reversed:
    def __call__(self, arr):
        l = len(arr)
        for idx in xrange(l):
            v = arr[l - idx - 1]
            yield v


class Sum:
    def __call__(self, sequence, start=0):
        return reduce(lambda x,y: x+y, sequence, start)


class XRangeInstance:
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
                return Generator.__pyfora_builtins__.MappingGenerator(self, f)

            def filter(self, f):
                return Generator.__pyfora_builtins__.FilteringGenerator(self, f)

            def nest(self, subgeneratorFun):
                return Generator.__pyfora_builtins__.NestedGenerator(self, subgeneratorFun)

            def associativeReduce(self, initValSoFar, add, merge, empty):
                """__without_stacktrace_augmentation"""

                return __inline_fora("""
                    fun(initValSoFar, start, increment, add, merge, empty, count) {
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


class XRange:
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


class Sorted:
    def __call__(self, iterable):
        if isinstance(iterable, list):
            return Sorted._sortList(iterable)
        else:
            return Sorted._sortList([val for val in iterable])

    @staticmethod
    def _sortList(xs):
        return Sorted.__pyfora_builtins__.sorted(xs)


class Round:
    def __call__(self, x):
        f = math.floor(x)

        if abs(x - f) < 0.5:
            return f

        return f + 1


mappings_ = [
    (abs, Abs), (all, All), (any, Any),
    (apply, None), (basestring, None), (bin, None),
    (buffer, None), (bytearray, None),
    #note that bytes in python2.7 is actually the same object as 'str'
    #which is already implemented in the NamedSingletons
    #(bytes, None), 
    (callable, None), (chr, Chr),
    (classmethod, None), (cmp, None), (coerce, None),
    (compile, None), (copyright, None),
    (credits, None), (delattr, None),
    (dir, None), (divmod, None), (enumerate, Enumerate),
    (eval, None), (execfile, None), (exit, None),
    (file, None), (filter, None),
    (format, None), (frozenset, None), (getattr, None),
    (globals, None), (hasattr, None), (hash, None),
    (help, None), (hex, None), (id, None), (input, None),
    (intern, None), (iter, None), (len, Len),
    (license, None), (locals, None),
    (long, None), (map, Map), (max, Max),
    (memoryview, None), (min, Min), (next, None),
    (oct, None), (open, None),
    (ord, Ord), (pow, None),
    # (print, None), This syntax doesn't work for builtin print
    # because it isn't called with parens
    (property, None), (quit, None), (range, Range),
    (raw_input, None), (reduce, Reduce), (reload, None),
    (repr, None), (reversed, Reversed), (round, Round),
    (set, None), (setattr, None),
    (sorted, Sorted), (staticmethod, None),
    (sum, Sum), (super, None),
    (unichr, None), (unicode, None),
    (vars, None), (xrange, XRange), (zip, None)
    ]


def generateMappings():
    return [PureImplementationMapping.InstanceMapping(instance, pureType)
            for (instance, pureType) in mappings_]

