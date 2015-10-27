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

import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph

import logging

class FieldImpl(object):
    def __init__(self, f, setter):
        object.__init__(self)
        self.f = f
        self.setter = setter

    def __get__(self, obj, objType):
        if obj is None:
            return self

        return self.f(obj)
        
    def __call__(self, *args):
        return self.f(*args)

def Field(setter = None):
    """Decorator to indicate that a function implements an Object field.

    setter - None, or a function that accepts 'self' and a value to assign
    """
    def decorator(f):
        return FieldImpl(f, setter)

    return decorator

class FunctionImpl(object):
    def __init__(self, f):
        object.__init__(self)
        self.f = f

    def __get__(self, obj, objType):
        if obj is None:
            #when accessing this property on the class, return ourselves
            return self
        
        def closure(*args):
            return self.f(obj, *args)
        return closure

    def __call__(self, *args):
        return self.f(*args)

def Function():
    """Decorator to indicate that a function implements an executable.

    The function should accept 'self' and a json argument. It should
    return a json value.
    """
    def decorator(f):
        return FunctionImpl(f)

    return decorator


def isPropertyToExpose(classMember):
    if isinstance(classMember, FieldImpl):
        return True
    if isinstance(classMember, ComputedGraph.Key):
        return True
    if isinstance(classMember, (
                    ComputedGraph.Property, 
                    ComputedGraph.PropertyMaker, 
                    ComputedGraph.Mutable
                    )):
        return classMember.exposeToProtocol
    return False

def propertyHasSetter(classMember):
    if isinstance(classMember, (ComputedGraph.PropertyMaker, ComputedGraph.Mutable)):
        return True
    if isinstance(classMember, ComputedGraph.Key):
        return False
    return classMember.setter is not None

def isFunctionToExpose(classMember):
    if isinstance(classMember, FunctionImpl):
        return True

    if isinstance(classMember, ComputedGraph.Function):
        return classMember.exposeToProtocol

    return False

def functionExpectsExpandedArgs(classMember):
    if isinstance(classMember, ComputedGraph.Function):
        return classMember.expandArgs
    return False

def functionExpectsCallback(classMember):
    if isinstance(classMember, ComputedGraph.Function):
        return classMember.wantsCallback
    return False

def getSetter(fieldname, classMember):
    if isinstance(classMember, (ComputedGraph.Mutable, ComputedGraph.Property, ComputedGraph.PropertyMaker)):
        def setter(object, value):
            setattr(object, fieldname, value)
        return setter
    else:
        return classMember.setter

