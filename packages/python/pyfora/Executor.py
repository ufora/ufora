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
Executor

Responsible for sending python computations to a Ufora cluster and returns
their result
"""


import pyfora.Future as Future
import pyfora.Exceptions as Exceptions
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.WithBlockExecutor as WithBlockExecutor
import pyfora.DefaultPureImplementationMappings as DefaultPureImplementationMappings
import traceback
import logging
import threading


class Executor(object):
    """Submits computations to a Ufora cluster and marshals data to/from the local Python.

    The Executor is the main point of interaction with a Ufora cluster.
    It is responible for sending computations to the Ufora cluster and returning
    the result as a RemotePythonObject future.

    It is modeled after the same-named abstraction in the `concurrent.futures`_ module
    that is part of the Python3 standard library.

    All interactions with the remote cluster are asynchronous and return :class:`~Future.Future`
    objects that represent the in-progress operation.

    Python objects are sent to the server using the :func:`~Executor.define` method, which returns
    a :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
    corresponding to the submitted object.

    Similarly, functions and their arguments can be submitted using the :func:`~Executor.submit` method which
    returns a :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
    of the evaluated expression or raised exception.

    .. _concurrent.futures: https://pythonhosted.org/futures/

    Note:
        This class is not intended to be constructed explicitly. Instances of it
        are created by calling :func:`~pyfora.connect`.

    Args:
        connection (pyfora.Connection.Connection): an open connection to a Ufora cluster.
        pureImplementationMappings (optional): a :class:`~PureImplementationMappings.PureImplementationMappings`
            that defines mapping between Python libraries and their "pure" :mod:`pyfora` implementation.
    """
    def __init__(self, connection, pureImplementationMappings=None):
        self.connection = connection
        self.stayOpenOnExit = False
        self.pureImplementationMappings = pureImplementationMappings or DefaultPureImplementationMappings.getMappings()
        self.objectRegistry = ObjectRegistry.ObjectRegistry()
        self.objectRehydrator = PythonObjectRehydrator.PythonObjectRehydrator(self.pureImplementationMappings)
        self.futures = {}
        self.lock = threading.Lock()

    def importS3Dataset(self, bucketname, keyname):
        """Creates a :class:`~RemotePythonObject.RemotePythonObject` that represents the content of an S3 key as a string.

        Args:
            bucketname (str): The S3 bucket to read from.
            keyname (str): The S3 key to read.


        Returns:
            Future.Future: A :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            representing the content of the S3 key.
        """
        def importS3Dataset():
            builtins = bucketname.__pyfora_builtins__
            return builtins.loadS3Dataset(bucketname, keyname)

        return self.submit(importS3Dataset)

    def exportS3Dataset(self, valueAsString, bucketname, keyname):
        """Write a ComputedRemotePythonObject representing a :mod:`pyfora` string to S3

        Args:
            valueAsString (RemotePythonObject.ComputedRemotePythonObject): a computed string.
            bucketname (str): The name of the S3 bucket to write to.
            keyname (str): The S3 key to write to.

        Returns:
            Future.Future: A :class:`~Future.Future` representing the completion of the export operation.
            It resolves either to ``None`` (success) or to an instance of :class:`~Exceptions.PyforaError`.
        """
        assert isinstance(valueAsString, RemotePythonObject.ComputedRemotePythonObject)
        future = Future.Future()

        def onCompleted(result):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_result(None)

        self.connection.triggerS3DatasetExport(valueAsString, bucketname, keyname, onCompleted)

        return future

    def define(self, obj):
        """Create a remote representation of an object.

        Sends the specified object to the server and return a Future that resolves
        to a RemotePythonObject representing the object on the server.

        Args:
            obj: A python object to send

        Returns:
            Future.Future: A :class:`~Future.Future` that resolves to a
            :class:`~RemotePythonObject.RemotePythonObject` representing the object
            on the server.
        """

        self._raiseIfClosed()
        objectId = PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=self.pureImplementationMappings,
            objectRegistry=self.objectRegistry
            ).walkPyObject(obj)

        future = Future.Future()

        def onConverted(result):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_result(
                    RemotePythonObject.DefinedRemotePythonObject(
                        objectId,
                        self
                        )
                    )

        self.connection.convertObject(objectId, self.objectRegistry, onConverted)
        return future

    def submit(self, fn, *args, **kwargs):
        """Submits a callable to be executed on the cluster with the provided arguments.

        This function is shorthand for calling :func:`~Executor.define` on the callable and all
        arguments and then invoking the remote callable with the remoted arguments.

        Note:
            Keyword arguments (`**kwargs`) are not currently supported.

        Returns:
            Future.Future: A :class:`~Future.Future` representing the given call.
            The future eventually resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            instance or an exception.
        """
        self._raiseIfClosed()
        if len(kwargs) > 0:
            raise Exceptions.PyforaNotImplementedError("Keyword arguments not supported yet")

        # TODO: make this truly async
        #       don't block on the 'define' calls
        futures = [self.define(fn)] + [self.define(arg) for arg in args]
        results = [f.result() for f in futures]
        return results[0](*results[1:])


    def close(self):
        """Closes the connection to the Ufora cluster."""
        if not self.isClosed():
            self.connection.close()
            self.connection = None

    @property
    def remotely(self):
        """Returns a :class:`WithBlockExecutor.WithBlockExecutor` that can be used to enter a block of
        "pure" Python code.

        The ``with fora.remotely:`` syntax allows you to automatically submit an
        entire block of python code for remote execution. All the code nested in
        the remotely ``with`` block is submitted.

        Returns:
            WithBlockExecutor.WithBlockExecutor: A :class:`~WithBlockExecutor.WithBlockExecutor` that extracts
            python code from a with block and submits it to the Ufora cluster for
            remote execution.  Results of the remote execution are returned as
            RemotePythonObject and are automatically reasigned to their corresponding
            local variables in the with block.
            """
        return WithBlockExecutor.WithBlockExecutor(self)

    def isClosed(self):
        """Determine if the :class:`~Executor.Executor` is connected to the cluster.

        Returns:
            bool: ``True`` if :func:`~Executor.close` has been called, ``False`` otherwise.
        """

        return self.connection is None


    def __enter__(self):
        return self


    def __exit__(self, excType, excValue, trace):
        if not self.stayOpenOnExit:
            self.close()


    def _raiseIfClosed(self):
        if self.connection is None:
            raise Exceptions.PyforaError('Attempted operation on a closed executor')


    def _resolveFutureToComputedObject(self, future):
        future.set_result(
            RemotePythonObject.ComputedRemotePythonObject(
                future._executorState,
                self
                )
            )


    def _downloadComputedValueResult(self, computation, maxBytecount):
        future = Future.Future()

        def onResultCallback(jsonResult):
            try:
                if isinstance(jsonResult, Exception):
                    future.set_exception(jsonResult)
                    return

                if 'foraToPythonConversionError' in jsonResult:
                    future.set_exception(
                        Exceptions.ForaToPythonConversionError(
                            str(jsonResult['foraToPythonConversionError'])
                            )
                        )
                    return
                if not jsonResult['isException']:
                    if 'maxBytesExceeded' in jsonResult:
                        future.set_exception(Exceptions.ResultExceededBytecountThreshold())
                    else:
                        result = self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result'])
                        future.set_result(result)
                else:
                    result = self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result'])
                    future.set_exception(Exceptions.ComputationError(result, jsonResult['trace']))
            except Exception as e:
                # TODO need a better way of wrapping exceptions.
                # Alexandros has some ideas here, but this is
                # better than the experience without the wrapping
                # (which is hanging)
                def clip(s):
                    if len(s) > 250:
                        return s[:250] + "... (" + str(len(s) - 250) + " characters remaining)"
                    return s
                logging.error(
                    "Rehydration failed: %s\nResult was %s of type %s",
                    traceback.format_exc(),
                    clip(repr(jsonResult)),
                    type(jsonResult)
                    )

                future.set_exception(
                    Exceptions.ForaToPythonConversionError(
                        e
                        )
                    )

        self.connection.downloadComputation(computation, onResultCallback, maxBytecount)

        return future

    def _expandComputedValueToDictOfAssignedVarsToProxyValues(self, computedValue):
        future = Future.Future()

        def onExpanded(jsonResult):
            if isinstance(jsonResult, Exception):
                future.set_exception(jsonResult)
                return

            if jsonResult['isException']:
                result = self.objectRehydrator.convertJsonResultToPythonObject(
                    jsonResult['result']
                    )
                future.set_exception(
                    Exceptions.ComputationError(
                        result,
                        jsonResult['trace']
                        )
                    )
                return

            assert isinstance(jsonResult['dictOfProxies'], dict)

            dictOfProxies = {}
            for k, v in jsonResult['dictOfProxies'].iteritems():
                dictOfProxies[k] = RemotePythonObject.ComputedRemotePythonObject(v, self)

            future.set_result(dictOfProxies)

        self.connection.expandComputedValueToDictOfAssignedVarsToProxyValues(
            computedValue,
            onExpanded
            )

        return future


    def _expandComputedValueToTupleOfProxies(self, computedValue):
        future = Future.Future()

        def onExpanded(jsonResult):
            if isinstance(jsonResult, Exception):
                future.set_exception(jsonResult)
                return

            if jsonResult['isException']:
                result = self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result'])
                future.set_exception(Exceptions.ComputationError(result, jsonResult['trace']))
                return

            assert isinstance(jsonResult['tupleOfComputedValues'], tuple)

            tupleOfProxies = \
                tuple([
                    RemotePythonObject.ComputedRemotePythonObject(val, self) \
                    for val in jsonResult['tupleOfComputedValues']
                    ])

            future.set_result(tupleOfProxies)

        self.connection.expandComputedValueToTupleOfProxies(computedValue, onExpanded)

        return future


    def _downloadDefinedObject(self, objectId):
        future = Future.Future()
        def onRetrieved(value):
            future.set_result(value)
        self.connection.retrieveConvertedObject(objectId, onRetrieved)
        return future


    def _callRemoteObject(self, fnHandle, argHandles):
        future = Future.Future(onCancel=self._cancelComputation)
        def onComputationCreated(result):
            if isinstance(result, Exception):
                future.set_exception(result)
                return
            computation = result
            future.setExecutorState(computation)
            with self.lock:
                self.futures[computation] = future
            self._prioritizeComputation(future)

        self.connection.createComputation(fnHandle, argHandles, onComputationCreated)
        return future

    def _prioritizeComputation(self, future):
        computation = future._executorState
        def onPrioritized(result):
            if isinstance(result, Exception):
                future.set_exception(result)
            else:
                future.set_running_or_notify_cancel()

        def onComputationCompleted(shouldBeNone):
            self._resolveFutureToComputedObject(future)

        def onComputationFailed(exception):
            assert isinstance(exception, Exceptions.PyforaError)
            future.set_exception(exception)

        self.connection.prioritizeComputation(
            computation,
            onPrioritized,
            onComputationCompleted,
            onComputationFailed
            )

    def _cancelComputation(self, computationId):
        with self.lock:
            future = self.futures.get(computationId)
            if future is None:
                # the computation has already completed
                return False
            del self.futures[computationId]
        self.connection.cancelComputation(computationId)
        return True
