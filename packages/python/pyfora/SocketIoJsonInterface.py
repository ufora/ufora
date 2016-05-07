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

import json
from socketIO_client import SocketIO, BaseNamespace, TimeoutError, ConnectionError
from socketIO_client.transports import WebsocketTransport

import time
import threading

import pyfora


class ConnectionStatus(object):
    not_connected = 0
    connecting = 1
    connected = 2
    disconnected = 3

    def __init__(self):
        self.status = self.not_connected
        self.message = None


class SocketIoJsonInterface(object):
    def __init__(self,
                 url,
                 socketIONamespace,
                 events=None,
                 version=None):
        if url.endswith('/'):
            # remove trailing slash
            url = url[:-1]
        self.url = url
        self.path = socketIONamespace
        self.events = events or {}
        self.version = version or pyfora.__version__

        self.socketIO = None
        self.reactorThread = None
        self.namespace = None
        self.nextMessageId = 0
        self.messageHandlers = {}
        self.lock = threading.Lock()
        self.connection_cv = threading.Condition(self.lock)
        self.connection_status = ConnectionStatus()


    def connect(self, timeout=None):
        timeout = timeout or 30.0
        with self.lock:
            if self._isConnected():
                raise ValueError("'connect' called when already connected")

        with self.lock:
            t0 = time.time()
            self.connection_status.status = ConnectionStatus.connecting
            while True:
                try:
                    self.socketIO = SocketIO(self.url, wait_for_connection=False)
                    break
                except (TimeoutError, ConnectionError):
                    if time.time() - t0 > timeout:
                        raise
                    time.sleep(0.5)

            self.reactorThread = threading.Thread(target=self.socketIO.wait)

            if isinstance(self.socketIO._transport_instance, WebsocketTransport):
                self.socketIO._transport_instance._connection.lock = threading.Lock()

            self.reactorThread.daemon = True
            self.namespace = self.socketIO.define(self._namespaceFactory, self.path)
            self.reactorThread.start()

            while self.connection_status.status == ConnectionStatus.connecting and \
                    (time.time() - t0 < timeout):
                self.connection_cv.wait(timeout)

        if self.connection_status.status == ConnectionStatus.connected:
            return self

        if self.connection_status.status == ConnectionStatus.connecting:
            message = "Connection timed out"
        else:
            message = self.connection_status.message
        raise pyfora.ConnectionError(message)


    def close(self):
        with self.lock:
            if not self._isConnected():
                return
            reactorThread = self.reactorThread
            self.reactorThread = None
            self.socketIO.disconnect()
        reactorThread.join()


    def isConnected(self):
        with self.lock:
            return self._isConnected()


    def send(self, message, callback):
        with self.lock:
            self._raiseIfNotConnected()
            messageId = self.nextMessageId
            self.nextMessageId += 1
            self.messageHandlers[messageId] = callback

            def encoder(obj):
                if not isinstance(obj, dict) and hasattr(obj, 'toMemoizedJSON'):
                    return obj.toMemoizedJSON()
                return obj

            message['messageId'] = messageId
            self.namespace.emit('message', {'body': json.dumps(message, default=encoder)})


    def on(self, event, callback):
        if event in self.events:
            raise ValueError("Event handler for '%s' already exists" % event)
        self.events[event] = callback


    def _isConnected(self):
        return self.connection_status.status in [ConnectionStatus.connecting,
                                                 ConnectionStatus.connected]


    def _raiseIfNotConnected(self):
        if not self._isConnected():
            raise ValueError('Performing I/O on disconnected socket')


    def _namespaceFactory(self, *args, **kwargs):
        return Namespace(self._onConnected, *args, **kwargs)


    def _triggerEvent(self, event, *args, **kwargs):
        if event in self.events:
            self.events[event](*args, **kwargs)


    def _onConnected(self, namespace):
        namespace.on('disconnect', self._on_disconnect)

        namespace.on('handshake', self._on_handshake)
        namespace.emit('handshake', {'version': self.version})


    def _on_handshake(self, handshake_response):
        with self.lock:
            if handshake_response == 'ok':
                self.connection_status.status = ConnectionStatus.connected
            else:
                self.connection_status.status = ConnectionStatus.disconnected
                self.connection_status.message = handshake_response
            self.connection_cv.notify()

        self.namespace.on('response', self._on_message)


    def _on_message(self, payload):
        def object_hook(obj):
            for k in obj:
                if isinstance(obj[k], unicode):
                    obj[k] = obj[k].encode("utf8")
            return obj
        try:
            message = json.loads(payload, object_hook=object_hook)
        except:
            self._triggerEvent('invalid_message', payload)
            return

        messageId = message.get('messageId')
        if messageId is None:
            self._triggerEvent('special_message', message)
            return

        callback = self.messageHandlers.get(messageId)
        if callback is None:
            self._triggerEvent('unexpected_message', message)
            return

        if message.get('responseType') != 'SubscribeResponse':
            del self.messageHandlers[messageId]

        callback(message)


    def _on_disconnect(self):
        callbacks = []
        with self.lock:
            self.connection_status.status = ConnectionStatus.disconnected
            self.connection_cv.notify()

            # respond to all pending messages with a failure
            callbacks = [
                (cb, self._disconnect_failure_message(messageId))
                for messageId, cb in self.messageHandlers.iteritems()
                ]
            self.messageHandlers.clear()

        self._triggerEvent('disconnect')

        for callback, message in callbacks:
            callback(message)

    def _disconnect_failure_message(self, messageId):
        return {
            "messageId": messageId,
            "responseType": "Failure",
            "message": "Disconnected from server"
            }



class Namespace(BaseNamespace):
    def __init__(self, onConnected, *args, **kwargs):
        super(Namespace, self).__init__(*args, **kwargs)
        self.onConnected = onConnected

    def on_connect(self):
        self.onConnected(self)

