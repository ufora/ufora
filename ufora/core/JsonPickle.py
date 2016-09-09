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

"""JsonPickle

A simplified form of 'pickle' that only pickles ComputedGraph locations and 'simple' python
objects (e.g. those for whom eval(repr(x)) == x).

In this case, we don't pickle to a string - we pickle to 'simple' python objects, which are
very close to json.
"""

import sys

class Pickleable(object):
    """Mixin class to indicate that a class supports JsonPickle serialization. Classes
    must expose methods

    __reduce__(self):
        return (cls, ({..kwds},))

    we will then call cls(**kwds) to inflate. cls must descend from 'Pickleable'.

    By default, we just use the dict of the object and its own type
    """
    def __reduce__(self):
        return (type(self), (self.__dict__,))


#set of other classes we are allowed to unpickle. Mostly to allow for boost::python
#classes, which can't easily descend from 'Pickleable'
unpickleWhitelist_ = set()

def addClassToPickleWhitelist(cls):
    """Add a class that doesn't descend from Pickleable to the pickle whitelist"""
    unpickleWhitelist_.add(cls)


ENCODING_OBJECT = 'o'
ENCODING_SIMPLE_PYTHON = 'P'
ENCODING_UNICODE = 'u'
ENCODING_INT = 'i'
ENCODING_LONG = 'l'
ENCODING_TUPLE = '()'
ENCODING_LIST = '[]'
ENCODING_DICT = '{}'

#a dictionary from string to ComputedGraph.Location subclasses
locationTypes_ = {}

#a dictionary from a ComputedGraph type to a key that can be used in place of the usual
#(clsModule, clsName) pair
locationTypeOverrides_ = {}

def addOverride(cls, override):
    """Override the serializer to use 'override' as the identifier for instances of 'cls'

    This is primarily to shorted the amount of data in the representation and to allow the
    representation to remain constant even if classes are moving around or changing names.

    override may not be a tuple
    """
    assert cls not in locationTypeOverrides_
    assert not isinstance(override, tuple)

    locationTypeOverrides_[cls] = override
    locationTypes_[override] = cls

def addClassAlias(cls, override):
    locationTypes_[override] = cls

def classFromModuleAndName(clsModuleAndName):
    if clsModuleAndName in locationTypeOverrides_:
        return locationTypeOverrides_[clsModuleAndName]

    if clsModuleAndName not in locationTypes_:
        __import__(clsModuleAndName[0])

        try:
            module = sys.modules[clsModuleAndName[0]]
        except KeyError:
            raise UserWarning("Couldn't import module %s", clsModuleAndName[0])

        try:
            cls = module.__dict__[clsModuleAndName[1]]
        except KeyError:
            raise UserWarning("Can't find %s in %s" % (clsModuleAndName[1], module.__name__))
        if not issubclass(cls, Pickleable) and cls not in unpickleWhitelist_:
            raise UserWarning("%s is not a computed graph location type"  % clsModuleAndName)

        locationTypes_[clsModuleAndName] = cls

    return locationTypes_[clsModuleAndName]

def toSimple(complexObject):
    if complexObject is None:
        return (ENCODING_SIMPLE_PYTHON, None)

    if isinstance(complexObject, (float, str, bool)):
        return (ENCODING_SIMPLE_PYTHON, complexObject)

    if isinstance(complexObject, int):
        return (ENCODING_INT, str(complexObject))

    if isinstance(complexObject, long):
        return (ENCODING_LONG, str(complexObject))

    if isinstance(complexObject, unicode):
        return (ENCODING_UNICODE, complexObject.encode('utf-8'))

    if isinstance(complexObject, tuple):
        subs = []
        allArePurePython = True
        for x in complexObject:
            encoding, simpleForm = toSimple(x)
            if encoding != ENCODING_SIMPLE_PYTHON:
                allArePurePython = False
            subs.append((encoding, simpleForm))
        if allArePurePython:
            return (ENCODING_SIMPLE_PYTHON, complexObject)

        return (ENCODING_TUPLE, tuple(subs))

    if isinstance(complexObject, list):
        subs = []

        return (ENCODING_LIST, tuple([toSimple(x) for x in complexObject]))

    if isinstance(complexObject, dict):
        subs = []

        for key, val in complexObject.iteritems():
            keyEncoded = toSimple(key)
            valEncoded = toSimple(val)

            subs.append((keyEncoded, valEncoded))

        return (ENCODING_DICT, tuple(sorted(subs)))

    try:
        cls, args = complexObject.__reduce__()
    except:
        raise UserWarning("Couldn't call __reduce__ on %s", complexObject)
    if cls in locationTypeOverrides_:
        clsKey = locationTypeOverrides_[cls]
    else:
        clsKey = (cls.__module__, cls.__name__)

    return (ENCODING_OBJECT, (clsKey, toSimple(args[0])))


def toComplex(simpleObject):
    """Convert 'x' from a simplified form to the full CG form."""
    if simpleObject[0] == ENCODING_SIMPLE_PYTHON:
        return simpleObject[1]

    if simpleObject[0] == ENCODING_INT:
        return int(simpleObject[1])

    if simpleObject[0] == ENCODING_UNICODE:
        return unicode(simpleObject[1], 'utf-8')

    if simpleObject[0] == ENCODING_LONG:
        return long(simpleObject[1])

    if simpleObject[0] == ENCODING_TUPLE:
        return tuple([toComplex(x) for x in simpleObject[1]])

    if simpleObject[0] == ENCODING_LIST:
        return [toComplex(x) for x in simpleObject[1]]

    if simpleObject[0] == ENCODING_DICT:
        return dict((toComplex(k), toComplex(v)) for k,v in simpleObject[1])

    elif simpleObject[0] == ENCODING_OBJECT:
        clsModuleAndName = simpleObject[1][0]
        args = simpleObject[1][1]
        cls = classFromModuleAndName(clsModuleAndName)
        kwds = toComplex(args)
        try:
            return cls(**kwds)
        except:
            raise UserWarning("Failed to construct instance of %s with %s" % (cls, kwds))


    raise UserWarning("Badly encoded object")

import ufora.native.Json as JsonNative

def toJson(complexObject):
    return JsonNative.Json.fromSimple(toSimple(complexObject))

def fromJson(jsonForm):
    return toComplex(jsonForm.toSimple())


