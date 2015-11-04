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
Connection

Manages a connection to a Ufora cluster
"""

import pyfora.Exceptions as Exceptions
import pyfora.Executor as Executor
import pyfora.ObjectConverter as ObjectConverter
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.SocketIoJsonInterface as SocketIoJsonInterface
import pyfora.SubscribableWebObjects as SubscribableWebObjects
import pyfora.ModuleDirectoryStructure as ModuleDirectoryStructure
import pyfora
import os

class Connection(object):
    """Connection - a live connection to a Ufora cluster that can execute submitted
    Python code.

    This is an internal implementation class that is primarily used by Executor.Executor.
    """
    def __init__(self, webObjectFactory, converter):
        """Initialize a Connection object to a Ufora cluster.

        webObjectFactory - an instance of SubscribableWebObjects.WebObjectFactory.
        converter - object implementing ObjectConverter.ObjectConverter, or None for the default converter.
        """
        self.objectConverter = converter
        self.webObjectFactory = webObjectFactory
        self.closed = False

    def triggerS3DatasetExport(self, valueAsString, bucketname, keyname, onCompletedCallback):
        if not isinstance(valueAsString, RemotePythonObject.ComputedRemotePythonObject):
            onCompletedCallback(Exceptions.PyforaError("The argument to triggerS3DatasetExport should be a ComputedRemotePythonObject"))
            return
        if not isinstance(valueAsString.computedValue, SubscribableWebObjects.PyforaComputedValue):
            onCompletedCallback(Exceptions.PyforaError("The object handle in the object passed to triggerS3DatasetExport should be a ComputedValue"))
            return

        #first, ensure that the value itself resolves
        computedValue = valueAsString.computedValue
        computedValueToCalculate = self.webObjectFactory.ComputedValueForMember(
            {'baseComputedValue':computedValue,
             'memberName': '@pyfora_string_as_paged_vec_of_char'}
            )

        def onFailure(err):
            if not self.closed:
                onCompletedCallback(Exceptions.PyforaError(err['message']))
        def isFinishedChanged(isFinished):
            if not self.closed and isFinished:
                self.triggerS3DatasetExportOnFinishedCalculation(
                    computedValueToCalculate,
                    bucketname,
                    keyname,
                    onCompletedCallback
                    )

        def subscribeToFinished(result):
            computedValueToCalculate.subscribe_isFinished({
                'onSuccess': isFinishedChanged,
                'onFailure': onFailure,
                'onChanged': isFinishedChanged
                })

        computedValueToCalculate.increaseRequestCount({}, {'onSuccess':subscribeToFinished, 'onFailure':onFailure})


    def triggerS3DatasetExportOnFinishedCalculation(self, computedValue, bucketname, keyname, onCompletedCallback):
        def onSuccess(writeToS3TaskObject):
            #we have received a WriteToS3Task computed graph location
            self.subscribeToWriteToS3TaskResultAndCallCallback(writeToS3TaskObject, onCompletedCallback)

        def onFailure(err):
            onCompletedCallback(Exceptions.PyforaError(err['message']))

        computedValue.writeToS3(
            {'bucketname': bucketname, 'keyname': keyname},
            {'onSuccess': onSuccess, 'onFailure': onFailure}
            )

    def subscribeToWriteToS3TaskResultAndCallCallback(self, writeToS3TaskObject, onCompletedCallback):
        def onSuccess(result):
            if not self.closed and result is not None:
                if result['success']:
                    onCompletedCallback(None)
                else:
                    onCompletedCallback(Exceptions.PyforaError(result['message']))

        def onFailure(err):
            onCompletedCallback(Exceptions.PyforaError(err['message']))

        writeToS3TaskObject.subscribe_successOrError({
            'onSuccess': onSuccess,
            'onChanged': onSuccess,
            'onFailure': onFailure
            })



    def convertObject(self, objectId, objectRegistry, callback):
        def wrapper(*args, **kwargs):
            if not self.closed:
                callback(*args, **kwargs)
        self.objectConverter.convert(objectId, objectRegistry, wrapper)

    def createComputation(self, fn, args, onCreatedCallback):
        """Create a computation representing fn(*args).

        onCreatedCallback - called after defining the object.
            called with an Exception.PyforaError if there is an error,
            otherwise, called with a ComputedValue object representing the computation
        """
        assert isinstance(fn, RemotePythonObject.RemotePythonObject)
        assert all([isinstance(arg, RemotePythonObject.RemotePythonObject) for arg in args])

        computedValue = self.webObjectFactory.PyforaComputedValue({
            'argIds': (fn._pyforaComputedValueArg(),) + tuple(arg._pyforaComputedValueArg() for arg in args)
            })

        def onFailure(err):
            if not self.closed:
                onCreatedCallback(Exceptions.PyforaError(err))
        def onSuccess(computationId):
            if not self.closed:
                onCreatedCallback(computedValue)
        def onChanged(computationId):
            pass

        computedValue.subscribe_submittedComputationId({
            'onSuccess': onSuccess,
            'onFailure': onFailure,
            'onChanged': onChanged
            })

    def prioritizeComputation(self, computedValue, onPrioritizedCallback, onCompletedCallback, onFailedCallback):
        """Prioritize a given computation.

        computedValue - the callback result of creating a computation.
        onPrioritizedCallback - called with either an error or None on success of the prioritization
        onCompletedCallback - called with None if the computation finishes with a value
        onFailedCallback - called with a pyfora exception if the computation fails or throws an exception for some reason
        """
        def onFailure(err):
            if not self.closed:
                onPrioritizedCallback(Exceptions.PyforaError(err))
        def onSuccess(result):
            if not self.closed:
                onPrioritizedCallback(None)
                self._subscribeToComputationStatus(computedValue, onCompletedCallback, onFailedCallback)

        computedValue.increaseRequestCount({}, {
            'onSuccess': onSuccess,
            'onFailure': onFailure
            })

    def expandComputedValueToDictOfAssignedVarsToProxyValues(self, computedValue, onExpanded):
        """Given a computedValue that should represent a dictionary, expand it to a dictionary of ComputedValues.

        If it's not a dictionary, or something else happens, this will resolve to a PyforaError.
        """
        def onResult(result):
            if result is not None and not self.closed:
                onExpanded(result)

        def onFailure(result):
            if isinstance(result, Exception):
                onExpanded(result)
            else:
                onExpanded(
                    Exceptions.PyforaError(
                        "Unknown error translating to dictionary of proxies: %s" + str(result)
                        )
                    )

        computedValue.increaseRequestCount({}, {'onSuccess': lambda *args: None, 'onFailure': lambda *args: None})
        computedValue.subscribe_pyforaDictToAssignedVarsToComputedValues({
            'onSuccess': onResult,
            'onFailure': onFailure,
            'onChanged': onResult
            })


    def expandComputedValueToTupleOfProxies(self, computedValue, onExpanded):
        def onResult(result):
            if result is not None and not self.closed:
                onExpanded(result)

        def onFailure(result):
            if isinstance(result, Exception):
                onExpanded(result)
            else:
                onExpanded(
                    Exceptions.PyforaError(
                        "Unknown error translating to dictionary of proxies: %s" + str(result)
                        )
                    )

        computedValue.increaseRequestCount({}, {'onSuccess': lambda *args: None, 'onFailure': lambda *args: None})
        computedValue.subscribe_pyforaTupleToTupleOfComputedValues({
            'onSuccess': onResult,
            'onFailure': onFailure,
            'onChanged': onResult
            })



    def _subscribeToComputationStatus(self, computedValue, onCompletedCallback, onFailedCallback):
        def statusChanged(jsonStatus):
            if not self.closed:
                if jsonStatus is not None:
                    if jsonStatus['status'] == 'failure':
                        onFailedCallback(Exceptions.PyforaError(jsonStatus['message']))
                    else:
                        onCompletedCallback(None)

        def onFailure(err):
            if not self.closed:
                onFailedCallback(Exceptions.PyforaError(err))

        computedValue.subscribe_jsonStatusRepresentation({
            'onSuccess': statusChanged,
            'onFailure': onFailure,
            'onChanged': statusChanged
            })

    def downloadComputation(self, computedValue, onResultCallback, maxBytecount=None):
        """download the result of a computation as json.

        onResultCallback - called with a PyforaError if there is a problem, or
            the json representation of the computation's result or exception otherwise.
        """
        def onFailure(err):
            if not self.closed:
                onResultCallback(Exceptions.PyforaError(err['message']))
        def resultChanged(jsonStatus):
            if not self.closed and jsonStatus is not None:
                onResultCallback(jsonStatus)

        computedValue.increaseRequestCount({}, {'onSuccess': lambda *args: None, 'onFailure': lambda *args: None})

        resultComputer = self.webObjectFactory.PyforaResultAsJson({'computedValue': computedValue, 'maxBytecount': maxBytecount})

        resultComputer.subscribe_result({
            'onSuccess': resultChanged,
            'onFailure': onFailure,
            'onChanged': resultChanged
            })

    def close(self):
        self.closed = True
        self.webObjectFactory.getJsonInterface().close()


def createObjectConverter(webObjectFactory):
    path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
    moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")

    return ObjectConverter.ObjectConverter(webObjectFactory, moduleTree.toJson())

def connect(url):
    """Connects to a Ufora cluster listening on the url and port provided by 'url'

    Returns:
        An executor object responsibe for submitting python code to the cluster for 
        execution returning RemotePythonObjects that can be used to download the 
        results from the server.
    """
    socketIoInterface = SocketIoJsonInterface.SocketIoJsonInterface(
        url,
        '/subscribableWebObjects'
        )
    socketIoInterface.connect()

    webObjectFactory = SubscribableWebObjects.WebObjectFactory(socketIoInterface)
    return Executor.Executor(Connection(webObjectFactory, createObjectConverter(webObjectFactory)))

def connectGivenSocketIo(socketIoInterface):
    webObjectFactory = SubscribableWebObjects.WebObjectFactory(socketIoInterface)
    return Executor.Executor(Connection(webObjectFactory, createObjectConverter(webObjectFactory)))


