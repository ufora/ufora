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

import pyfora.Future as Future
import pyfora.Exceptions as Exceptions
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.ObjectVisitors as ObjectVisitors
import pyfora.WithBlockExecutor as WithBlockExecutor
import pyfora.DefaultPureImplementationMappings as DefaultPureImplementationMappings
import traceback
import logging
import threading


class Executor(object):
    """Main executor for Pyfora code."""
    def __init__(self, connection, pureImplementationMappings=None):
        """Initialize a Pyfora executor.

        connection - a pyfora.Connection.Connection, or something with similar interface.
        """
        self.connection = connection
        self.stayOpenOnExit = False
        self.pureImplementationMappings = pureImplementationMappings or DefaultPureImplementationMappings.getMappings()
        self.objectRegistry = ObjectRegistry.ObjectRegistry()
        self.objectRehydrator = PythonObjectRehydrator.PythonObjectRehydrator(self.pureImplementationMappings)
        self.futures = {}
        self.lock = threading.Lock()

    def importS3Dataset(self, bucketname, keyname):
        def importS3Dataset():
            builtins = bucketname.__pyfora_builtins__
            return builtins.loadS3Dataset(bucketname, keyname)

        return self.submit(importS3Dataset)

    def exportS3Dataset(self, valueAsString, bucketname, keyname):
        """Write a ComputedRemotePythonObject representing a pyfora string to s3 and return a
        Future representing the completion of the object.

        The future will resolve either to None (success) or to a Exceptions.PyforaException.
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
        """Send 'obj' to the server and return a Future that resolves to a RemotePythonObject
        representing the object on the server.
        """

        self._raiseIfClosed()
        objectId = ObjectVisitors.walkPythonObject(
            obj,
            self.objectRegistry,
            self.pureImplementationMappings
            )

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
        """Submits a callable to be executed with the given arguments.

        Returns:
            A Future representing the given call. The future will eventually resolve to a
            RemotePythonObject instance.
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
        if not self.isClosed():
            self.connection.close()
            self.connection = None

    @property
    def remotely(self):
        return WithBlockExecutor.WithBlockExecutor(self)

    def isClosed(self):
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
                logging.error(
                    "Rehydration failed: %s\nResult was %s of type %s", 
                    traceback.format_exc(), 
                    jsonResult, 
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


