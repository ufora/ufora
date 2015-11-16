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
A proxy for some object, data or callable that lives in memory on a Ufora cluster
"""


import pyfora.Exceptions as Exceptions

class RemotePythonObject(object):
    """A local proxy for a python object that lives in memory on a Ufora cluster.

    This is an abstract class and should not be used directly, but through its two
    subclasses: :class:`~pyfora.RemotePythonObject.DefinedRemotePythonObject` and
    :class:`~pyfora.RemotePythonObject.ComputedRemotePythonObject`.

    Args:
        executor (Executor.Executor): a :class:`~pyfora.Executor.Executor`
    """
    def __init__(self, executor):
        self.executor = executor

    def toLocal(self):
        """Downloads the remote object.

        Returns:
            Future.Future: a :class:`~Future.Future` that resolves to the python
            object that this :class:`RemotePythonObject` represents.
        """
        raise Exceptions.PyforaNotImplementedError(
            "'%s' not implemented yet for type '%s'"
            % (self.toLocal.__name__,
               type(self).__name__)
            )

    def _pyforaComputedValueArg(self):
        """Argument to be passed to PyforaComputedValue to represent this object."""
        raise NotImplementedError()

    def __call__(self, *args):
        """Invoke a remoted function or callable object.

        Args:
            *args (List[RemotePythonObject]): arguments to pass to the callable.
                They must be instances of :class:`RemotePythonObject`.

        Returns:
            Future.Future: a :class:`~pyfora.Future.Future` that resolves to a
                :class:`RemotePythonObject` that represents the return value of
                the remote function call.
        """
        assert all([isinstance(arg, RemotePythonObject) for arg in args])
        return self.executor._callRemoteObject(self, args)

class DefinedRemotePythonObject(RemotePythonObject):
    """A proxy that represents a local object, which has been uploaded to a Ufora cluster.

    Note:
        Only :class:`~Executor.Executor` is intended to create instances of
        :class:`DefinedRemotePythonObject`. They are created by calling
        :func:`~pyfora.Executor.Executor.define`.

    Args:
        objectId (int): a value that uniquely identifies the remote object that
            this :class:`DefinedRemotePythonObject` represents.
        executor (Executor.Executor): the :class:`~pyfora.Executor.Executor` that created this
            :class:`DefinedRemotePythonObject`.
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
    """A proxy that represents a remote object created on a Ufora cluster as a
    result of some computation.

    Note:
        Only :class:`~Executor.Executor` is intended to create instances of
        :class:`ComputedRemotePythonObject`. They are created by calling
        :func:`~pyfora.Executor.Executor.define`.

    Args:
        computedValue: an instance of a SubscribableWebObject computedValue representing
            the computation that produced this :class:`ComputedRemotePythonObject`.
        executor (Executor.Executor): the :class:`~pyfora.Executor.Executor` that created this
            :class:`DefinedRemotePythonObject`.
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

