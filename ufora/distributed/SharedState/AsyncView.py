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

import Queue
import logging
import threading
import traceback
import time
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.util.ManagedThread as ManagedThread
import ufora.util.Deferred as Deferred
import ufora.native.Json as NativeJson


def createAllKeysRange(keyspace, dimension):
    return SharedState.KeyRange(keyspace, dimension, None, None, True, False)

class Disconnected(object):
    pass

class CallbackException(object):
    def __init__(self, exception):
        self.exception = exception


class AsyncView(object):
    def __init__(self,
            viewFactory,
            onConnectCallback=lambda result: None,
            onErrorCallback=lambda error: None):

        self._stopFlag = threading.Event()

        self._onConnectCallback = onConnectCallback
        self._onErrorCallback = onErrorCallback

        self._view = viewFactory.createView(retrySeconds = 10.0, numRetries = 10)
        self._listener = SharedState.Listener(self._view)

        self._subscribedKeyspaces = set()
        self._keyspaceCallbackFunctions = {}
        self._subscriptionDeferreds = {}
        self._reactorThreadCalls = Queue.Queue()

        self._viewReactorThread = ManagedThread.ManagedThread(target=self._viewReactorLoop)

    def assertSingleThreaded(self):
        assert self._viewReactorThread.ident == threading.currentThread().ident

    @property
    def id(self):
        self.assertSingleThreaded()
        return str(self._view.id)


    def _onError(self, error):
        '''
        Trigger the error flag if we aren't shutting down
        '''
        if not self._stopFlag.is_set():
            self._onErrorCallback(error)

    def subscribeToKey(self, keyspace, keyname, dimension, callback=None):
        '''
        Subscribe to a single key in a keyspace and optionally receive notifications
        of changes via a callback.

        callback signature:

        callback(items) : where items is a dictionary from (SharedState.Key -> string)

        '''
        self.assertSingleThreaded()
        keyrange = SharedState.KeyRange(keyspace, dimension, keyname, keyname, True, True)
        return self.subscribeToKeyspace(
                keyspace, dimension, callback, keyrange=keyrange)

    def subscribeToKeyspace(self, keyspace, dimension, callback = None, keyrange = None):
        '''
        Subscribe to a keyspace and optionally receive notifications of changes via
        a callback.

        callback signature:

        callback(items) : where items is a dictionary from (SharedState.Key -> string)

        '''
        self.assertSingleThreaded()
        assert not keyspace.name in self._keyspaceCallbackFunctions
        # in order to make things as simple as possible we only allow one
        # subscription per keyspace. This can be modified in the future
        if keyrange is None:
            keyrange = createAllKeysRange(keyspace, dimension)

        assert keyrange.keyspace == keyspace
        assert keyspace.name not in self._subscriptionDeferreds, \
                "already subscribed to %s" % keyspace.name
        assert keyspace.name not in self._keyspaceCallbackFunctions

        tr = Deferred.Deferred()
        self._subscriptionDeferreds[keyspace.name] = tr
        if callback is not None:
            self._keyspaceCallbackFunctions[keyspace.name] = callback
        self._view.subscribe(keyrange, False)
        self._subscribedKeyspaces.add(keyspace.name)
        return tr

    def keyspaceIterItems(self, keyspace):
        self.assertSingleThreaded()
        startKey = tuple([NativeJson.lowestValue() for x in range(keyspace.dimension)])
        with SharedState.Transaction(self._view):
            k = self._view.nextKey(SharedState.Key(keyspace, startKey))
            while k is not None and str(k.keyspace) == str(keyspace.name):
                if self._view[k] is not None:
                    yield k, self._view[k].value()
                k = self._view.nextKey(k)

    def keyspaceItems(self, keyspace):
        self.assertSingleThreaded()
        return [item for item in self.keyspaceIterItems(keyspace)]

    def startService(self):
        self._viewReactorThread.start()

    def stopService(self):
        logging.debug("Stopping AsyncView")
        self._stopFlag.set()
        self._listener.wake()
        if self._viewReactorThread.ident != threading.currentThread().ident:
            logging.debug("Joining view reactor thread")
            self._viewReactorThread.join()

        self._view.teardown()


    def getValue(self, key):
        self.assertSingleThreaded()
        assert not self._stopFlag.is_set()

        if key.keyspace not in self._subscribedKeyspaces:
            raise UserWarning("Must be subscribed to a keyspace before pushing a transaction")

        with SharedState.Transaction(self._view):
            valueHolder = self._view[key]
            if valueHolder is None:
                raise KeyError()
            return valueHolder.value()

    def pushTransaction(self, key, value, callback = None, errback = None):
        assert not self._stopFlag.is_set()
        if key.keyspace not in self._subscribedKeyspaces:
            raise UserWarning("Must be subscribed to a keyspace before pushing a transaction")

        self.reactorThreadCall(self.makePushTransactionCallable(key,value), callback, errback)

    def makePushTransactionCallable(self, key, value):
        def callable():
            with SharedState.Transaction(self._view):
                self._view[key] = value
        return callable

    def reactorThreadCall(self, callable, callback=None, errback=None):
        self._reactorThreadCalls.put((callable, callback, errback))
        self._listener.wake()

    def _waitConnect(self):
        t0 = time.time()
        while not self._stopFlag.is_set():
            if self._view.waitConnectTimeout(.1):
                self._onConnectCallback(None)
                return
            else:
                if time.time() - t0 > 5:
                    logging.info('waiting for view to connect')
                    t0 = time.time()

        self._onError(Disconnected())

    def _handleKeyUpdates(self, keys):
        assert len(keys)
        toCallback = {}
        with SharedState.Transaction(self._view):
            for key in keys:
                if key.keyspace in self._keyspaceCallbackFunctions:
                    if not key.keyspace in toCallback:
                        toCallback[key.keyspace] = []
                    toCallback[key.keyspace].append((key, self._view[key].value()))
        for keyspaceName, changedPairs in toCallback.iteritems():
            try:
                self._keyspaceCallbackFunctions[keyspaceName](dict(changedPairs))
            except Exception as e:
                logging.error('exception calling callback\n%s', ''.join(traceback.format_exc()))
                self._onError(CallbackException(e))

    def _handleKeyspaceUpdate(self, keyspace):
        keyspaceName = keyspace.keyspace.name
        if keyspaceName in self._subscriptionDeferreds:
            try:
                self._subscriptionDeferreds[keyspaceName].callback(None)
            except:
                logging.error(
                    'Exception raised calling callback for %s:\n%s',
                    keyspaceName,
                    traceback.format_exc()
                    )
            finally:
                del self._subscriptionDeferreds[keyspaceName]

    def _handleReactorThreadCalls(self):
        while not self._stopFlag.is_set():
            try:
                callable, callback, errback = self._reactorThreadCalls.get_nowait()
                try:
                    tr = callable()
                    if callback:
                        callback(tr)
                except Exception as e:
                    if errback:
                        errback(e)
                    else:
                        logging.error("Error during reactorThread call: %s threw exception %s",
                            callable,
                            traceback.format_exc(e)
                            )
            except Queue.Empty:
                return

    def _viewReactorLoop(self):
        self._waitConnect()
        while not self._stopFlag.is_set():
            try:
                updateList = self._listener.get()
                if not self._listener.isConnected:
                    logging.info("AsyncView: Lost connection to SharedState")
                    self._onError(Disconnected())

                for updateType, update in updateList:
                    if updateType == "KeyUpdates":
                        self._handleKeyUpdates(update)
                    elif updateType == "SubscriptionEnd":
                        self._handleKeyspaceUpdate(update)

                self._handleReactorThreadCalls()

            except UserWarning:
                if not self._stopFlag.is_set():
                    logging.error(
                            "AsyncView: error in updateLoop:\n %s",
                            traceback.format_exc()
                            )
                    self._onError(Disconnected())
                else:
                    #this can be a 'debug' level log, since errors pushing to SharedState during
                    #shutdown are due to disconnections
                    logging.debug(
                            "AsyncView: error in updateLoop:\n %s",
                            traceback.format_exc()
                            )

                return
        self._onError(Disconnected())





