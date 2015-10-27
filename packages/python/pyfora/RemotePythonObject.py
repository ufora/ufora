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

import pyfora.Exceptions as Exceptions

class RemotePythonObject(object):
    """RemotePythonObject

    Represents a wrapped python object on the ufora server, held locally by proxy.

    We have subclasses that implement values that are held locally (because
    we defined them and sent them to the server) and remotely (because
    they were the result of a computation)
    """

    def __init__(self, executor):
        """Initialize a RemotePythonObject

        executor - a pyfora.Executor
        """
        self.executor = executor

    def toLocal(self):
        """Produce a Future that resolves to the actual python object
        that this RemotePythonObject represents."""
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.toLocal.__name__,
               type(self).__name__)
            )

    def _pyforaComputedValueArg(self):
        """Argument to be passed to PyforaComputedValue to represent this object."""
        raise NotImplementedError()

    def __call__(self, *args):
        assert all([isinstance(arg, RemotePythonObject) for arg in args])
        return self.executor._callRemoteObject(self, args)

class DefinedRemotePythonObject(RemotePythonObject):
    """A remote python object that we defined locally and uploaded.

    objectId - an integer defining the object
    executor - a pyfora.Executor
    """
    def __init__(self, objectId, executor):
        super(DefinedRemotePythonObject, self).__init__(executor)
        self.objectId = objectId

    def _pyforaComputedValueArg(self):
        """Argument to be passed to PyforaComputedValue to represent this object."""
        return self.objectId

    def toLocal(self):
        return self.executor._downloadDefinedObject(self.objectId)


class ComputedRemotePythonObject(RemotePythonObject):
    """A remote python object that we created by computing something on a Ufora cluster.

    computedValue - a SubscribableWebObject computedValue that represents the computation
    executor - a pyfora.Executor
    """
    def __init__(self, computedValue, executor):
        super(ComputedRemotePythonObject, self).__init__(executor)
        self.computedValue = computedValue

    def _pyforaComputedValueArg(self):
        """Argument to be passed to PyforaComputedValue to represent this object."""
        return self.computedValue

    def toLocal(self, maxBytecount=None):
        return self.executor._downloadComputedValueResult(self.computedValue, maxBytecount)

    def toDictOfProxies(self):
        return self.executor._expandComputedValueToDictOfProxies(self.computedValue)

    def toTupleOfProxies(self):
        return self.executor._expandComputedValueToTupleOfProxies(self.computedValue)

