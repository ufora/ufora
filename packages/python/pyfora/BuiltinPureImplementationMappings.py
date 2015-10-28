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

class Range:
    def __call__(self, first, second=None, increment=None):
        return [x for x in xrange(first, second, increment)]

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

    def __pyfora_summable__(self, f):
        if self.count <= 0:
            return None

        def sum(val,count,increment,depth):
            if count == 1:
                return f(val)

            if depth > 9:
                res = f(val)
                val = val + increment
                count = count - 1
                while count > 0:
                    res = res + f(val)
                    val = val + increment
                    count = count - 1
                return res
            else:
                lowCount = count / 2

                return (
                    sum(val, lowCount, increment, depth+1) + 
                    sum(val + lowCount * increment, count-lowCount, increment, depth+1)
                    )

        sum(self.start, self.count, self.increment, 0)

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
        #see if we can get a 'summation' interface
        summable = None
        try:
            #note that we don't use 'getattr', which is
            #currently not going to fully compile because it requires us to
            #convert symbols to strings
            summable = sequence.__pyfora_summable__
        except AttributeError:
            pass

        if summable is not None:
            return summable(lambda x:x)

        res = start
        for elt in sequence:
            res = res + elt
        return res

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
    (min, Min)
    ]

def generateMappings():
	return [PureImplementationMapping.InstanceMapping(instance, pureType) for (instance, pureType) in mappings_]

