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
RemotePythonObject

A proxy to some object, data or callable that lives in memory on the Ufora
cluster
"""


import pyfora.Exceptions as Exceptions

class RemotePythonObject(object):
    """RemotePythonObject exposes a python object which lives in memory on the Ufora
    cluster, but is also referenced locally by proxy.

    There are two subclasses of RemotePythonObject corresponding to two different
    types of remote objects:

        - DefinedRemotePythonObject - objects that were created locally and remoted
            to the Ufora cluster
        - ComputedRemotePythonObject - an object that is the result of a computation 
            that ran on the Ufora cluster
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

    def toDictOfAssignedVarsToProxyValues(self):
        return self.executor._expandComputedValueToDictOfAssignedVarsToProxyValues(self.computedValue)

    def toTupleOfProxies(self):
        return self.executor._expandComputedValueToTupleOfProxies(self.computedValue)

