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

Manages a connection to a pyfora cluster
"""

import pyfora.Exceptions as Exceptions
import pyfora.Executor as Executor
import pyfora.ObjectConverter as ObjectConverter
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.SocketIoJsonInterface as SocketIoJsonInterface
import pyfora.ModuleDirectoryStructure as ModuleDirectoryStructure
import threading

# We defer importing SubscribableWebObjects.py to support auto doc generation
# on readthedocs.org without running a full build.
#import pyfora.SubscribableWebObjects as SubscribableWebObjects

import pyfora
import os

class Connection(object):
    """A live connection to a pyfora cluster that can execute submitted Python code.

    Note:
        This is an internal implementation class that is primarily used by
        :class:`~pyfora.Executor.Executor`.

    Args:
        webObjectFactory (SubscribableWebObjects.WebObjectFactory): A factory
            for subscribable web objects.
        converter (Optional ObjectConverter.ObjectConverter): an optional object
            converter or None for the default converter.
    """
    def __init__(self, webObjectFactory, converter):
        self.objectConverter = converter
        self.webObjectFactory = webObjectFactory
        self.closed = False

        self.viewOfEntireSystem = self.webObjectFactory.ViewOfEntireCumulusSystem({})

        self.subscribeToMessages()
        self.logMessageHandler = None

    def subscribeToMessages(self):
        def onSuccess(messages):
            if self.closed:
                return

            self.pullAllMessages()

        def onChanged(messages):
            if self.closed:
                return

            self.pullAllMessages()

            self.subscribeToMessages()

        def onFailure(err):
            pass

        self.viewOfEntireSystem.subscribe_totalMessagesEver({
            'onSuccess': onSuccess,
            'onFailure': onFailure,
            'onChanged': onChanged
            })

    def pullAllMessages(self):
        processed = threading.Event()

        def onSuccess(messages):
            try:
                for m in messages:
                    if self.logMessageHandler:
                        self.logMessageHandler(m)
                    else:
                        if not m['isDeveloperFacing']:
                            print m['message'],
            finally:
                processed.set()

        def onFailure(err):
            processed.set()

        self.viewOfEntireSystem.clearAndReturnMostRecentMessages({}, {
            'onSuccess': onSuccess,
            'onFailure': onFailure
            })

        return processed

    def pullAllMessagesAndProcess(self):
        self.pullAllMessages().wait()




    def triggerS3DatasetExport(self,
                               valueAsString,
                               bucketname,
                               keyname,
                               onCompletedCallback):
        if not isinstance(valueAsString, RemotePythonObject.ComputedRemotePythonObject):
            onCompletedCallback(
                Exceptions.PyforaError(
                    "The argument to triggerS3DatasetExport should be a ComputedRemotePythonObject"
                    )
                )
            return

        import pyfora.SubscribableWebObjects as SubscribableWebObjects
        if not isinstance(valueAsString.computedValue, SubscribableWebObjects.PyforaComputedValue):
            onCompletedCallback(
                Exceptions.PyforaError(
                    ("The object handle in the object passed to triggerS3DatasetExport should be a "
                     "ComputedValue")
                    )
                )
            return

        #first, ensure that the value itself resolves
        computedValue = valueAsString.computedValue
        computedValueToCalculate = self.webObjectFactory.ComputedValueForMember(
            {
                'baseComputedValue': computedValue,
                'memberName': '@pyfora_string_as_paged_vec_of_char'
            })

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

        computedValueToCalculate.increaseRequestCount(
            {},
            {'onSuccess':subscribeToFinished, 'onFailure':onFailure}
            )


    def getClusterStatus(self, onCompletedCallback):
        clusterStatus = self.webObjectFactory.PyforaCluster({})
        def onSuccess(clusterStatus):
            onCompletedCallback(clusterStatus)

        def onFailure(err):
            onCompletedCallback(Exceptions.PyforaError(err['message']))

        clusterStatus.getClusterStatus({}, {
            'onSuccess': onSuccess,
            'onFailure': onFailure
            })


    def triggerS3DatasetExportOnFinishedCalculation(self,
                                                    computedValue,
                                                    bucketname,
                                                    keyname,
                                                    onCompletedCallback):
        def onSuccess(writeToS3TaskObject):
            #we have received a WriteToS3Task computed graph location
            self.subscribeToWriteToS3TaskResultAndCallCallback(writeToS3TaskObject,
                                                               onCompletedCallback)

        def onFailure(err):
            onCompletedCallback(Exceptions.PyforaError(err['message']))

        computedValue.writeToS3(
            {'bucketname': bucketname, 'keyname': keyname},
            {'onSuccess': onSuccess, 'onFailure': onFailure}
            )


    def subscribeToWriteToS3TaskResultAndCallCallback(self,
                                                      writeToS3TaskObject,
                                                      onCompletedCallback):
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

        computation = self.webObjectFactory.Computation({
            'arg_ids': (fn._pyforaComputedValueArg(), ) + tuple(
                arg._pyforaComputedValueArg() for arg in args
                )
            })

        def onFailure(err):
            if not self.closed:
                onCreatedCallback(Exceptions.PyforaError(err))
        def onSuccess(_):
            if not self.closed:
                onCreatedCallback(computation)

        computation.get_computation_id({
            'onSuccess': onSuccess,
            'onFailure': onFailure
            })


    def start_computation(self,
                          computation,
                          onStartedCallback,
                          onCompletedCallback,
                          onFailedCallback):
        """Prioritize a given computation.

        computation - the callback result of creating a computation.
        onStartedCallback - called with either an error or None if the computation
                            was started successfully
        onCompletedCallback - called with the "jsonStatus" if the computation finishes with a value
        onFailedCallback - called with a pyfora exception if the computation fails
            or throws an exception for some reason
        """
        def onFailure(err):
            if not self.closed:
                onStartedCallback(Exceptions.PyforaError(err))
        def onSuccess(_):
            if not self.closed:
                onStartedCallback(None)
                self._subscribeToComputationStatus(computation,
                                                   onCompletedCallback,
                                                   onFailedCallback)

        computation.start({}, {
            'onSuccess': onSuccess,
            'onFailure': onFailure
            })


    def computation_from_id(self, computation_id):
        return self.webObjectFactory.Computation(
            {
                'comp_id': computation_id
            })


    def triggerCompilationOnComputation(self, computation, onCompleted):
        """Trigger compilation of the code underlying a computation.

        This is exclusively used for testing purposes, as it only works when
        there is a single in-process cumulus node.

        Returns True on success, False on failure.
        """
        def callback(_):
            onCompleted()

        computation.triggerCompilation({}, {
            'onSuccess': callback,
            'onFailure': callback
            })


    @staticmethod
    def cancelComputation(computedValue):
        """Cancel a computation."""
        def completed(_):
            pass
        computedValue.cancel({}, {
            'onSuccess': completed,
            'onFailure': completed
        })


    def expandComputedValueToDictOfAssignedVarsToProxyValues(self, computation, onExpanded):
        """Given a computedValue that should represent a dictionary,
        expand it to a dictionary of ComputedValues.

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

        computation.get_as_dictionary({
            'onSuccess': onResult,
            'onFailure': onFailure
            })


    def expandComputedValueToTupleOfProxies(self, computation, onExpanded):
        def onResult(result):
            if result is not None and not self.closed:
                onExpanded(result)

        def onFailure(result):
            if isinstance(result, Exception):
                onExpanded(result)
            else:
                onExpanded(
                    Exceptions.PyforaError(
                        "Unknown error expanding tuple: %s" + str(result)
                        )
                    )

        computation.get_as_tuple({
            'onSuccess': onResult,
            'onFailure': onFailure
            })



    def _subscribeToComputationStatus(self, computation, onCompletedCallback, onFailedCallback):
        def statusChanged(jsonStatus):
            if not self.closed:
                if jsonStatus is not None:
                    if jsonStatus['status'] == 'failure':
                        onFailedCallback(Exceptions.PyforaError(jsonStatus['message']))
                    else:
                        onCompletedCallback(jsonStatus)

        def onFailure(err):
            if not self.closed:
                onFailedCallback(Exceptions.PyforaError(err))

        computation.subscribe_computation_status({
            'onSuccess': statusChanged,
            'onFailure': onFailure,
            'onChanged': statusChanged
            })


    def downloadComputation(self, computation, onResultCallback, maxBytecount=None):
        """download the result of a computation as json.

        onResultCallback - called with a PyforaError if there is a problem, or
            the json representation of the computation's result or exception otherwise.
        """
        def onFailure(err):
            if not self.closed:
                onResultCallback(Exceptions.PyforaError(err['message']))

        subscribed_to_result = [False]

        def resultChanged(jsonStatus):
            if self.closed:
                return
            if jsonStatus is None and not subscribed_to_result[0]:
                subscribed_to_result[0] = True
                computation.subscribe_result({
                    'onSuccess': resultChanged,
                    'onFailure': onFailure,
                    'onChanged': resultChanged
                    })
            elif jsonStatus is not None:
                onResultCallback(jsonStatus)

        def resultStatusChanged(populated):
            if not self.closed and populated:
                computation.request_result({'maxBytecount': maxBytecount}, {
                    'onSuccess': resultChanged,
                    'onFailure': onFailure
                    })

        self._subscribeToComputationStatus(computation,
                                           resultStatusChanged,
                                           onFailure)


    def close(self):
        self.closed = True
        self.webObjectFactory.getJsonInterface().close()


def createObjectConverter(webObjectFactory):
    path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
    moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")

    return ObjectConverter.ObjectConverter(webObjectFactory, moduleTree.toJson())


def connect(url, timeout=30.0):
    """Opens a connection to a pyfora cluster

    Args:
        url (str): The HTTP URL of the cluster's manager (e.g. ``http://192.168.1.200:30000``)
        timeout (Optional float): A timeout for the operation in seconds, or None
            to wait indefinitely.

    Returns:
        An :class:`~pyfora.Executor.Executor` that can be used to submit work
        to the cluster.
    """
    socketIoInterface = SocketIoJsonInterface.SocketIoJsonInterface(
        url,
        '/subscribableWebObjects'
        )
    socketIoInterface.connect(timeout=timeout)
    return connectGivenSocketIo(socketIoInterface)


def connectGivenSocketIo(socketIoInterface):
    import pyfora.SubscribableWebObjects as SubscribableWebObjects
    webObjectFactory = SubscribableWebObjects.WebObjectFactory(socketIoInterface)
    return Executor.Executor(Connection(webObjectFactory, createObjectConverter(webObjectFactory)))


