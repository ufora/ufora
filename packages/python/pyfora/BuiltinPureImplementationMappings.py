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
        start = 0
        stop = 0
        if second == None:
            stop = first
        else:
            start = first
            stop = second

        if increment == None:
            increment = 1
        
        toReturn = []
        currentVal = start

        while currentVal < stop:
            toReturn = toReturn + [currentVal]
            currentVal = currentVal + increment
        return toReturn

class XRange:
    def __call__(self, first, second=None, increment=None):
        # this is some unfortunate code duplication
        # Range() should really return list(xrange())
        # but that isn't converting properly right now
        # --Amichai
        start = 0
        stop = 0
        if second == None:
            stop = first
        else:
            start = first
            stop = second

        if increment == None:
            increment = 1
        
        currentVal = start

        while currentVal < stop:
            yield currentVal
            currentVal = currentVal + increment



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



mappings_ = [(len, Len), (str, Str), (range, Range), (xrange, XRange), (abs, Abs), (all, All)]

def generateMappings():
	return [PureImplementationMapping.InstanceMapping(instance, pureType) for (instance, pureType) in mappings_]

