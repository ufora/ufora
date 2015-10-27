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

import ufora.BackendGateway.SubscribableWebObjects.Decorators as Decorators
import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions
import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.distributed.SharedState.ComputedGraph as CGSS
import ufora.distributed.SharedState.ComputedGraph.Node
import ufora.distributed.SharedState.ComputedGraph.Property
import time
import threading

class TestCGLocation(ComputedGraph.Location):
    definition = ComputedGraph.Key(object)
    aValue = ComputedGraph.Mutable(lambda: None, exposeToProtocol = True)

    def sharedStateSubspace(self):
        return CGSS.Node.Keyspace(keyspacePath=("public", "writeable", "TestCGLocation")).subspace

    aValueInSharedState = CGSS.Property.Property(default = lambda: False, exposeToProtocol = True)
    bValueInSharedState = CGSS.Property.Property(default = lambda: False, exposeToProtocol = True)
    cValueInSharedState = CGSS.Property.Property(default = lambda: False, exposeToProtocol = True)

    @ComputedGraph.ExposedProperty()
    def depth(self):
        if isinstance(self.definition, Test):
            return self.definition.depth + 1
        elif isinstance(self.definition, list):
            res = 0
            for x in self.definition:
                res += x.depth
            return res
        else:
            return 0

    @ComputedGraph.ExposedProperty()
    def testCgLocation(self):
        return self

    @ComputedGraph.ExposedFunction()
    def aFunction(self, jsonArg):
        self.aValue = jsonArg

    @ComputedGraph.Function
    def anUnexposedFunction(self, jsonArg):
        self.aValue = jsonArg

    @ComputedGraph.ExposedFunction()
    def testFunction(self, arg):
        return arg

    @ComputedGraph.ExposedFunction(wantsCallback = True)
    def aFunctionExpectingCallback(self, callback, jsonArg):
        def aThread():
            time.sleep(1)
            callback(jsonArg)
        threading.Thread(target=aThread).start()

class Test(object):
    """Model for the current number of active and desired cumulus cores."""
    def __init__(self, jsonDefinition):
        object.__init__(self)
        self.definition = jsonDefinition
        self.location = TestCGLocation(definition=self.definition)

    @Decorators.Field()
    def depth(self):
        if isinstance(self.definition, Test):
            return self.definition.depth + 1
        elif isinstance(self.definition, list):
            res = 0
            for x in self.definition:
                res += x.depth
            return res
        else:
            return 0

    @Decorators.Function()
    def aFunction(self, jsonArg):
        self.location.aValue = len(jsonArg)

    @Decorators.Field()
    def aFloat(self):
        """Returns the number .5"""
        return .5

    def setMutableValue(self, value):
        self.location.aValue = value

    @Decorators.Field(setter=setMutableValue)
    def mutableValue(self):
        """a mutable value"""
        return self.location.aValue

    def setAValueThrowingAnArbitraryException(self, value):
        assert False

    @Decorators.Field(setter=setAValueThrowingAnArbitraryException)
    def aValueThrowingAnArbitraryException(self):
        assert False

    @Decorators.Function()
    def aFunctionThrowingAnArbitraryException(self, jsonArgs):
        assert False

    @Decorators.Function()
    def aFunctionNotReturningJson(self, jsonArgs):
        return Test

    @Decorators.Field()
    def aFieldNotReturningJson(self):
        return Test

    @Decorators.Function()
    def aFunctionNotAcceptingAnyArguments(self):
        return None

    def setAValueThrowingASpecificException(self, value):
        raise Exceptions.SubscribableWebObjectsException("swo exception: setter")

    @Decorators.Field(setter=setAValueThrowingASpecificException)
    def aValueThrowingASpecificException(self):
        raise Exceptions.SubscribableWebObjectsException("swo exception: getter")

    @Decorators.Function()
    def aFunctionThrowingASpecificException(self, jsonArgs):
        raise Exceptions.SubscribableWebObjectsException("swo exception: function call")

    def setAValueInSharedState(self, value):
        self.location.aValueInSharedState = value

    @Decorators.Field(setter=setAValueInSharedState)
    def aValueInSharedState(self):
        """a mutable value held in shared state"""
        return self.location.aValueInSharedState

    def setBValueInSharedState(self, value):
        self.location.bValueInSharedState = value

    @Decorators.Field(setter=setBValueInSharedState)
    def bValueInSharedState(self):
        """a mutable value held in shared state"""
        return self.location.bValueInSharedState

    def setCValueInSharedState(self, value):
        self.location.cValueInSharedState = value

    @Decorators.Field(setter=setCValueInSharedState)
    def cValueInSharedState(self):
        """a mutable value held in shared state"""
        return self.location.cValueInSharedState


