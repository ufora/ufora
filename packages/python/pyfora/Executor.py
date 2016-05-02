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

Responsible for sending python computations to a pyfora cluster and returns
their result
"""


import pyfora.Future as Future
import pyfora.Exceptions as Exceptions
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.WithBlockExecutor as WithBlockExecutor
import pyfora.PureImplementationMappings as PureImplementationMappings
import traceback
import logging
import threading


class Executor(object):
    """Submits computations to a pyfora cluster and marshals data to/from the local Python.

    The Executor is the main point of interaction with a pyfora cluster.
    It is responible for sending computations to the cluster and returning
    the result as a RemotePythonObject future.

    It is modeled after the same-named abstraction in the `concurrent.futures`_ module
    that is part of the Python3 standard library.

    All interactions with the remote cluster are asynchronous and return :class:`~Future.Future`
    objects that represent the in-progress operation.

    Python objects are sent to the server using the :func:`~Executor.define` method, which returns
    a :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
    corresponding to the submitted object.

    Similarly, functions and their arguments can be submitted using the
    :func:`~Executor.submit` method which returns a :class:`~Future.Future` that
    resolves to a :class:`~RemotePythonObject.RemotePythonObject` of the evaluated
    expression or raised exception.

    .. _concurrent.futures: https://pythonhosted.org/futures/

    Note:
        This class is not intended to be constructed explicitly. Instances of it
        are created by calling :func:`~pyfora.connect`.

    Args:
        connection (pyfora.Connection.Connection): an open connection to a cluster.
        pureImplementationMappings (optional): a
            :class:`~PureImplementationMappings.PureImplementationMappings`
            that defines mapping between Python libraries and their "pure" :mod:`pyfora`
            implementation.
    """
    def __init__(self, connection, pureImplementationMappings=None):
        self.connection = connection
        self.stayOpenOnExit = False
        self.pureImplementationMappings = \
            pureImplementationMappings or PureImplementationMappings.PureImplementationMappings()
        self.objectRegistry = ObjectRegistry.ObjectRegistry()
        self.objectRehydrator = PythonObjectRehydrator.PythonObjectRehydrator(
            self.pureImplementationMappings
            )
        self.lock = threading.Lock()

    def importS3Dataset(self, bucketname, keyname, verify=True):
        """Creates a :class:`~RemotePythonObject.RemotePythonObject` that represents
        the content of an S3 key as a string.

        Args:
            bucketname (str): The S3 bucket to read from.
            keyname (str): The S3 key to read.
            verify: Throw an exception immediately if the key or bucket cannot be read.


        Returns:
            A :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            representing the content of the S3 key.
        """
        def importS3Dataset():
            return __inline_fora(
                """fun(@unnamed_args:(bucketname, keyname), *args) {
                       purePython.PyforaBuiltins.loadS3Dataset(bucketname, keyname)
                       }"""
                )(bucketname, keyname)

        future = self.submit(importS3Dataset)

        if verify:
            result = future.result()
            if result.isException:
                try:
                    result.toLocal().result()
                except Exception as e:
                    raise e

        return future

    def exportS3Dataset(self, valueAsString, bucketname, keyname):
        """Write a ComputedRemotePythonObject representing a :mod:`pyfora` string to S3

        Args:
            valueAsString (RemotePythonObject.ComputedRemotePythonObject): a computed string.
            bucketname (str): The name of the S3 bucket to write to.
            keyname (str): The S3 key to write to.

        Returns:
            A :class:`~Future.Future` representing the completion of the export operation.
            It resolves either to ``None`` (success) or to an instance of :class:`~pyfora.PyforaError`.
        """
        assert isinstance(valueAsString, RemotePythonObject.ComputedRemotePythonObject)
        future = self._create_future()
        def onComplete(result):
            self._resolve_future(future, result)
        self.connection.triggerS3DatasetExport(valueAsString,
                                               bucketname,
                                               keyname,
                                               onComplete)
        return future

    def importRemoteFile(self, path):
        """Loads the content of a file as a string

        Note:
            The file must be available to all machines in the cluster using
            the specified path. If you run multiple workers you must either copy
            the file to all machines, or if using a network file-system, mount
            it into the same path on all machines.

            In addition, pyfora may cache the content of the file. Changes to the
            file's content made after it has been loaded may have no effect.

        Args:
            path (str): Full path to the file. This must be a valid path on **all**
                worker machines in the cluster.

        Returns:
            A :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            representing the content of the file as a string.
        """
        def importFile():
            return __inline_fora(
                """fun(@unnamed_args:(path), *args) {
                       purePython.PyforaBuiltins.loadFileDataset(path)
                       }"""
                )(path)

        return self.submit(importFile)

    def define(self, obj):
        """Create a remote representation of an object.

        Sends the specified object to the server and return a Future that resolves
        to a RemotePythonObject representing the object on the server.

        Args:
            obj: A python object to send

        Returns:
            A :class:`~Future.Future` that resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            representing the object on the server.
        """

        self._raiseIfClosed()
        try:
            objectId = PyObjectWalker.PyObjectWalker(
                purePythonClassMapping=self.pureImplementationMappings,
                objectRegistry=self.objectRegistry
                ).walkPyObject(obj)
        except PyObjectWalker.UnresolvedFreeVariableExceptionWithTrace as e:
            logging.error(
                "Converting UnresolvedFreeVariableExceptionWithTrace to PythonToForaConversionError:\n%s",
                traceback.format_exc())
            raise Exceptions.PythonToForaConversionError(e.message, e.trace)
        future = self._create_future()

        def onConverted(result):
            if not isinstance(result, Exception):
                result = RemotePythonObject.DefinedRemotePythonObject(objectId, self)
            self._resolve_future(future, result)

        self.connection.convertObject(objectId, self.objectRegistry, onConverted)
        return future

    def submit(self, fn, *args):
        """Submits a callable to be executed on the cluster with the provided arguments.

        This function is shorthand for calling :func:`~Executor.define` on the callable and all
        arguments and then invoking the remote callable with the remoted arguments.

        Returns:
            A :class:`~Future.Future` representing the given call.
            The future eventually resolves to a :class:`~RemotePythonObject.RemotePythonObject`
            instance or an exception.
        """
        self._raiseIfClosed()

        # TODO: make this truly async
        #       don't block on the 'define' calls
        futures = [self.define(fn)] + [self.define(arg) for arg in args]
        results = [f.result() for f in futures]
        return results[0](*results[1:])


    def close(self):
        """Closes the connection to the pyfora cluster."""
        if not self.isClosed():
            self.connection.close()
            self.connection = None


    @property
    def remotely(self):
        """Returns a :class:`WithBlockExecutor.WithBlockExecutor` that can be used
        to enter a block of "pure" Python code.

        The ``with executor.remotely:`` syntax allows you to automatically submit an
        entire block of python code for remote execution. All the code nested in
        the remotely ``with`` block is submitted.

        Returns:
            A :class:`~WithBlockExecutor.WithBlockExecutor` that extracts python
            code from a with block and submits it to the pyfora cluster for
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


    def _create_future(self, onCancel=None):
        future = Future.Future(onCancel=onCancel)
        return future


    def _resolve_future(self, future, result):
        if isinstance(result, Exceptions.PyforaError):
            future.set_exception(result)
        else:
            future.set_result(result)


    def _resolveFutureToComputedObject(self, future, jsonResult):
        self._resolve_future(
            future,
            RemotePythonObject.ComputedRemotePythonObject(future._computedValue,
                                                          self,
                                                          'status' in jsonResult and jsonResult['status'] == "exception"
                                                          )
            )


    def _downloadComputedValueResult(self, computation, maxBytecount):
        future = self._create_future()

        def onResultCallback(jsonResult):
            result = jsonResult
            try:
                if not isinstance(jsonResult, Exception):
                    result = self._translate_download_result(jsonResult)
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
                result = Exceptions.ForaToPythonConversionError(e)
            self._resolve_future(future, result)

        self.connection.downloadComputation(computation, onResultCallback, maxBytecount)
        return future


    def _translate_download_result(self, jsonResult):
        if 'foraToPythonConversionError' in jsonResult:
            return Exceptions.ForaToPythonConversionError(
                str(jsonResult['foraToPythonConversionError'])
                )

        if not jsonResult['isException']:
            if 'maxBytesExceeded' in jsonResult:
                return Exceptions.ResultExceededBytecountThreshold()
            else:
                return self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result'])

        result = self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result'])
        return Exceptions.ComputationError(result, jsonResult['trace'])

    def _expandComputedValueToDictOfAssignedVarsToProxyValues(self, computedValue):
        future = self._create_future()

        def onExpanded(jsonResult):
            result = jsonResult
            if not isinstance(jsonResult, Exception):
                if jsonResult['isException']:
                    result = Exceptions.ComputationError(
                        self.objectRehydrator.convertJsonResultToPythonObject(jsonResult['result']),
                        jsonResult['trace']
                        )
                else:
                    assert isinstance(jsonResult['dictOfProxies'], dict)
                    result = {
                        k: RemotePythonObject.ComputedRemotePythonObject(v, self, False)
                        for k, v in jsonResult['dictOfProxies'].iteritems()
                        }
            self._resolve_future(future, result)

        self.connection.expandComputedValueToDictOfAssignedVarsToProxyValues(computedValue,
                                                                             onExpanded)

        return future


    def _expandComputedValueToTupleOfProxies(self, computedValue):
        future = self._create_future()

        def onExpanded(jsonResult):
            result = jsonResult
            if not isinstance(jsonResult, Exception):
                if jsonResult['isException']:
                    result = Exceptions.ComputationError(
                        self.objectRehydrator.convertJsonResultToPythonObject(
                            jsonResult['result']
                            ),
                        jsonResult['trace']
                        )
                else:
                    assert isinstance(jsonResult['tupleOfComputedValues'], tuple)
                    result = tuple(
                        RemotePythonObject.ComputedRemotePythonObject(val, self, False)
                        for val in jsonResult['tupleOfComputedValues']
                        )

            self._resolve_future(future, result)

        self.connection.expandComputedValueToTupleOfProxies(computedValue, onExpanded)
        return future


    def _downloadDefinedObject(self, objectId):
        future = self._create_future()
        def onRetrieved(value):
            self._resolve_future(future, value)
        self.connection.retrieveConvertedObject(objectId, onRetrieved)
        return future


    def _triggerCompilation(self, functionHandle, argHandles):
        future = self._create_future()

        def onCompleted():
            self._resolve_future(future, True)

        def onComputationCreated(result):
            self.connection.triggerCompilationOnComputation(result, onCompleted)

        self.connection.createComputation(functionHandle, argHandles, onComputationCreated)

        return future

    def _callRemoteObject(self, fnHandle, argHandles):
        future = self._create_future(onCancel=self._cancelComputation)
        def onComputationCreated(result):
            if isinstance(result, Exception):
                self._resolve_future(future, result)
                return
            computation = result
            
            future.setComputedValue(computation)
            self._prioritizeComputation(future)

        self.connection.createComputation(fnHandle, argHandles, onComputationCreated)
        return future

    def _prioritizeComputation(self, future):
        computation = future._computedValue
        def onPrioritized(result):
            if isinstance(result, Exception):
                self._resolve_future(future, result)
            else:
                future.set_running_or_notify_cancel()

        def onComputationCompleted(jsonResult):
            self._resolveFutureToComputedObject(future, jsonResult)

        def onComputationFailed(exception):
            assert isinstance(exception, Exceptions.PyforaError)
            self._resolve_future(future, exception)

        self.connection.prioritizeComputation(
            computation,
            onPrioritized,
            onComputationCompleted,
            onComputationFailed
            )

    def _cancelComputation(self, computation):
        self.connection.cancelComputation(computation)
        return True
