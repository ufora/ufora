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

"""
ComputedGraph

We begin with a set of classes which define the locations in which data is stored in the system.
Every client class C will tell us
    - keys
    - properties
    - mutables

Client code subclasses Location. Functions of one variable (self) become properties.
Class members that are types become keys. Class members that are decorated with Mutable become
Mutables. See the example.

We define a distinct set of potential Location objects for every client class consisting of (C, K)
where K is the set of all possible tuples the keys could take.
Two Locations that have the same class and keys have to be the same object.

Every location has a set of mutable pieces of information which are default initialized
(see class Mutable). These determine the state of the system.

Every location has a set of properties - these are computed by looking at the properties, keys,
and mutables of "self" and other locations. They cannot be circular.

The ComputableGraph class tracks the mutable properties and creates the relevant nodes of the graph
as defined by the properties. When mutable properties are modified, the computed nodes are dirtied,
and eventually re-computed. "Nodes" in ComputableGraph are pairs of (Location,Property),
(Location,Key), and (Location,Mutable)

The ComputableGraph doesn't track nodes that are orphaned, so we add "root" properties that
we'll keep alive.

see example at the end of the file.
"""

import time
import threading
import traceback
import logging
import sys
import ufora.core.JsonPickle as JsonPickle

import ufora.core.math.StableHashFunction as StableHashFunction
from ufora.util.PythonCodeUtils import isSimpleFunction
import ufora.util.ThreadLocalStack as ThreadLocalStack
import ufora.native.ScopedPythonTracer as ScopedPythonTracer


import ufora.native.ComputedGraph as cgModule
ComputedGraph = cgModule.ComputedGraph

#install a function to let us hash these
def hashComputedGraphLocation(loc, unhashableObjectPolicy):
    return StableHashFunction.stableShaHashForObject(
        (loc.__location_class__, loc.__reduce__()),
        unhashableObjectPolicy
        )
StableHashFunction.hashFunctionsByType[cgModule.LocationRef_] = hashComputedGraphLocation

threadLocalStack = ThreadLocalStack.ThreadLocalStack()

def pushCurGraph(x):
    threadLocalStack.push(x)

def popCurGraph():
    threadLocalStack.pop()

def currentGraph():
    return threadLocalStack.topOrNone

def assertHasGraph():
    assert currentGraph() != None


def isLocation(loc):
    """returns True if loc is a ComputedGraph location. False otherwise"""
    return isinstance(loc, cgModule.LocationRef_)

def isLocationOfType(loc, t):
    """returns True if loc is a ComputedGraph location. False otherwise"""
    return isLocation(loc) and issubclass(loc.__location_class__, t)

def getLocationTypeFromLocation(loc):
    return loc.__location_class__

functype = type(lambda:0)

def callFunc(f, args, k):
    return f(*args, **k)

class Location(JsonPickle.Pickleable):
    """base class that client code must subclass. Overrides "new" to get the relevant node from
       the current graph"""
    def __new__(cls, *a, **args):
        if len(a) == 1 and isinstance(a[0],dict):
            args = a[0]
        else:
            assert len(a) == 0, "tried to construct a " + str(cls) + " with non-keyword args"

        return currentGraph().getNode_(cls, args)

def executeWithinTryBlock(func, arg):
    try:
        tr = func(arg)

    except Exception , e:
        if 'orig_traceback' not in e.__dict__:
            e.__dict__['orig_traceback'] = sys.exc_info()
        return e

    return tr

def raiseException(ex):
    raise ex.orig_traceback[0], ex.orig_traceback[1], ex.orig_traceback[2]

converters = dict()

def convertItem(value):
    try:
        c = converters[type(value)]
    except:
        return ("arb",value)
    return c(value)

converters[tuple] = lambda value: (tuple, tuple([convertItem(k) for k in value]))
converters[dict] = lambda value: (dict, tuple([(key, convertItem(value[key])) for key in value]))
converters[int] = lambda value: value
converters[float] = lambda value: value
converters[long] = lambda value: value
converters[str] = lambda value: value
converters[unicode] = lambda value: str(value)
converters[cgModule.LocationRef_] = lambda value: ("CG", id(value))
converters[list] = converters[tuple]

class InstanceDataToIDLookupTable:
    def __init__(self):
        self.d = dict()

    def convert(self, classObject, argsDict):
        return (classObject, convertItem(argsDict))

    def __call__(self, classObject, argsDict):
        tup = self.convert(classObject, argsDict)
        if tup not in self.d:
            self.d[tup] = tup
        return id(self.d[tup])

    def kill(self, classObject, argsDict):
        tup = self.convert(classObject, argsDict)
        if tup in self.d:
            del self.d[tup]

class DependencyCycle(object):
    def __init__(self, cycle = None):
        self.cycle = cycle if cycle is not None else []
    def __str__(self):
        return 'Cycle: ' + ' -> '.join([str(x) for x in self.cycle])

class Mutable(object):
    def __init__(self, proptype, defaultValue = None, onUpdate = None, exposeToProtocol = False):
        self.proptype = proptype
        self.defaultValue = defaultValue
        self.onUpdate = onUpdate
        self.exposeToProtocol = exposeToProtocol

class Key(object):
    def __init__(self, t, default = None, validator = None):
        self.t = t
        self.default = default
        self.validator = validator

class NotCached(object):
    def __init__(self, f):
        self.f = f

class Function(object):
    def __init__(self, f, exposeToProtocol = False, expandArgs = False, wantsCallback = False):
        self.f = f
        self.expandArgs = expandArgs
        self.exposeToProtocol = exposeToProtocol
        self.wantsCallback = wantsCallback

    @property
    def func_code(self):
        return self.f.func_code

    @property
    def __name__(self):
        return self.f.__name__

    def __call__(self, *args, **args2):
        return self.f(*args, **args2)

def ExposedFunction(expandArgs = False, wantsCallback = False):
    """Create a function to expose over the socket.io protocol.

    expandArgs = pass the single socket.io args argument as a list or kwds argument.
    wantsCallback = this function's first argument is a callback which will contain the
        final result or exception.
    """
    def decorator(f):
        return Function(f, exposeToProtocol = True, expandArgs = expandArgs, wantsCallback = wantsCallback)
    return decorator

class Initializer(object):
    def __init__(self, f):
        self.f = f

class Property(object):
    def __init__(self, cacheFunc, setter = None, isLazy = False, exposeToProtocol = False):
        self.cacheFunc = cacheFunc
        self.setter = setter
        self.isLazy = isLazy
        self.exposeToProtocol = exposeToProtocol
    def asLazy(self):
        """return a copy of this Property marked 'lazy'"""
        return Property(self.cacheFunc, self.setter, True, self.exposeToProtocol)

def Lazy(cacheFuncOrProp):
    """CG decorator used to mark a property 'lazy'.

    A lazy property can be recomputed opportunistically based on resources
    available.  This allows interface code to separate things that must be
    recomputed to keep the interface up to date and background update code,
    which might take longer.
    """
    if isinstance(cacheFuncOrProp, Property):
        #it's already a property
        return cacheFuncOrProp.asLazy()
    else:
        return Property(cacheFuncOrProp, None, True)

class PropertyMaker(object):
    def __init__(self, f, exposeToProtocol = False):
        self.f = f
        self.exposeToProtocol = exposeToProtocol
    def __call__(self, name, cls):
        return self.f(name, cls)

class SimplePropertyMaker(PropertyMaker):
    def __init__(self, f):
        self.f = f
    def __call__(self, name, cls):
        return [(name, self.f(name, cls))]

def WithSetter(setter,exposeToProtocol = False):
    return lambda x: Property(x, setter, exposeToProtocol = exposeToProtocol)

def PropertyWithSetter(setter, exposeToProtocol = False):
    return lambda x: Property(x, setter, exposeToProtocol = exposeToProtocol)

def ExposedProperty():
    return lambda x: Property(x, None, exposeToProtocol = True)

def ExposedPropertyWithSetter(setter):
    return lambda x: Property(x, setter, exposeToProtocol = True)

def getClassMember(cls):
    if cls is object:
        return {}
    prior = {}
    def addMember(x, val):
        if isinstance(val, PropertyMaker):
            for x2, cls2 in val(x, cls):
                addMember(x2, cls2)
        elif x is not '__module__' and x is not '__doc__':
            if isinstance(x, Initializer) and x in prior:
                oldInit = prior[x].f
                newInit = val.f
                def finalInit(self):
                    oldInit(self)
                    newInit(self)
                prior[x] = Initializer(finalInit)
            else:
                prior[x] = val

    for c in reversed(cls.mro()):
        if c is not object:
            for x,val in c.__dict__.items():
                addMember(x, val)

    return prior



class Caller_:
    def __init__(self, f, node):
        self.f = f
        self.node = node
    def __call__(self, *args, **args2):
        try:
            return self.f(self.node, *args, **args2)
        except:
            f = self.f
            try:
                funcName = "function " + f.func_code.co_filename + ":" + str(f.func_code.co_firstlineno) + ".  " + f.__name__,
            except:
                funcName = "unprintable function object %f" % f

            logging.debug("Exception in ComputedGraph %s: %s", funcName, traceback.format_exc())
            raise
    def tup(self):
        return (Caller_, self.f, self.node, self.node.__graph__)
    def __hash__(self):
        return hash(self.tup())
    def __eq__(self, other):
        if isinstance(other, Caller_):
            return self.tup() == other.tup()
        return False


class Slot(Location):
    id = object
    value = Mutable(object, lambda: None)
curSlots = 0
def slot(initial, id = None):
    global curSlots
    curSlots += 1
    tr = Slot(id = curSlots if id is None else id)
    tr.value = initial
    return tr




class MemoizedFunctionLocation(Location):
    func = object
    args = object
    kwds = object

    def result(self):
        return self.func(*self.args, **self.kwds)

def Memoized(f):
    """Decorator to memoize any python function 'f'

    In practice, this means we create a ComputedGraph location depending on the code for 'f',
    all of the data it binds, and any cargumetns. Callers will not be recomputed unless the result
    changes.
    """

    def memoingVersionOfF(*args, **kwds):
        mf = MemoizedFunctionLocation(func = f, args = args, kwds = kwds)
        return mf.result

    return memoingVersionOfF


def MemoizedFunction(f):
    """Decoration to make a memoized ComputedGraph.Location function.

    Usage:

    class X(ComputedGraph.Location):
        ...

        @ComputedGraph.MemoizedFunction
        def someFunc(self, arg1, arg2, ...):
            ...

    Now 'someFunc' will be memoized on its arguments. Warning - this can be slow, but allows
    you to prevent propagation dirty state in the graph.
    """

    return Function(Memoized(f))

