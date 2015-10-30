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
import pyfora.PureImplementationMappings as PureImplementationMappings

class Len:
	def __call__(self, other):
		return other.__len__()

class Str:
	def __call__(self, other):
		return other.__str__()

class List:
    def __call__(self, other):
        generator = other.__pyfora_generator__()

        def listSum(subGenerator, depth):
            if depth > 9 or not subGenerator.canSplit() or True:
                result = []
                for val in subGenerator:
                    result = result + [val]
                return result
            else:
                split = subGenerator.split()
                if split is None:
                    raise TypeError("Generator should have split!")
                left = listSum(split[0], depth+1)
                right = listSum(split[1], depth+1)

                return left+right

        return listSum(generator, 0)

class Range:
    def __call__(self, first, second=None, increment=None):
        return list(xrange(first, second, increment))

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
        #eventually this class should inherit behaviors from "PyGeneratorBase"
        class Generator:
            def __init__(self, start, count, increment, mapFun, filterFun):
                self.start = start
                self.count = count
                self.increment = increment
                self.mapFun = mapFun
                self.filterFun = filterFun

            def __pyfora_generator__(self):
                return self

            def __iter__(self):
                ix = 0
                currentVal = self.start
                while ix < self.count:
                    if self.filterFun(currentVal):
                        yield self.mapFun(currentVal)
                    currentVal = currentVal + self.increment
                    ix = ix + 1

            def canSplit(self):
                return self.count > 1

            def split(self):
                if self.count <= 1:
                    return None

                lowCount = self.count / 2
                highCount = self.count - lowCount

                return (
                    Generator(self.start, lowCount, self.increment, self.mapFun, self.filterFun),
                    Generator(self.start + self.increment * lowCount, highCount, self.increment, self.mapFun, self.filterFun)
                    )

            def map(self, f):
                mapfun = lambda x: f(self.mapFun(x))
                return Generator(self.start, self.count, self.increment, mapfun, self.filterFun)

            def filter(self, f):
                filterfun = lambda x: f(x) and self.filterFun(x)
                return Generator(self.start, self.count, self.increment, self.mapFun, filterfun)


        return Generator(self.start, self.count, self.increment, lambda x:x, lambda x: True)

class XRange:
    def __call__(self, first, second=None, increment=None):
        start = 0
        stop = 0
        if second is None:
            stop = first
        else:
            start = first
            stop = second

        if increment is None:
            increment = 1

        if increment == 0:
            raise ValueError("xrange() arg 3 must not be zero")

        if increment > 0:
            count = max(0, (stop - start - 1) / increment + 1)
        else:
            count = max(0, (start - stop - 1) / (-increment) + 1 )

        return XRangeInstance(start, count, increment)

class Sum:
    def __call__(self, sequence, start=0):
        #get a generator
        generator = sequence.__pyfora_generator__()

        class Empty:
            pass

        def sum(sumSubGenerator, depth):
            if depth > 9 or not sumSubGenerator.canSplit():
                isFirst = True
                result = None
                for val in sumSubGenerator:
                    if isFirst:
                        result = val
                        isFirst = False
                    else:
                        result = result + val
                if isFirst:
                    return Empty
                return result
            else:
                split = sumSubGenerator.split()
                left = sum(split[0], depth+1)
                right = sum(split[1], depth+1)

                if left is Empty:
                    return right
                if right is Empty:
                    return left
                return left+right

        result = sum(generator, 0)

        if result is Empty:
            return start

        return start + result

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

class Ord:
    def __call__(self, character):        
        # assert we're getting a character of length 1
        if len(character) != 1:
            raise TypeError("ord() expected a character")

        return character.__pyfora_ord__()
        
class Chr:
    def __call__(self, asciiValue):
        return asciiValue.__pyfora_chr__()

class Max:
    def __call__(self, a,b):
        if a<b:
            return b
        return a

class Min:
    def __call__(self, a,b):
        if a<b:
            return a
        return b

mappings_ = [
    (len, Len), 
    (str, Str), 
    (range, Range), 
    (xrange, XRange), 
    (sum, Sum),
    (abs, Abs), 
    (all, All),
    (ord, Ord),
    (chr, Chr),
    (max, Max), 
    (min, Min),
    (list, List)
    ]

def generateMappings():
	return [PureImplementationMapping.InstanceMapping(instance, pureType) for (instance, pureType) in mappings_]

