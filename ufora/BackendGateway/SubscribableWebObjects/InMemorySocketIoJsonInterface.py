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

"""Creates an in-memory SubscribableWebObjects backend and wires it to a SocketIoJsonInterface"""

import json
import threading
import Queue
import logging
import traceback
import cProfile
import StringIO
import pstats

GRAPH_UPDATE_TIME = 0.01

class InMemorySocketIoJsonInterface(object):
    def __init__(self, messageProcessorFactory, enableProfiling=False):
        self.messageProcessor = messageProcessorFactory()
        self.events = {}
        self.reactorThread = None
        self.nextMessageId = 0
        self.messageHandlers = {}

        self.lock = threading.Lock()
        self.messageQueue = Queue.Queue()

        if enableProfiling:
	        self.profiler = cProfile.Profile()
        else:
            self.profiler = None

        with self.lock:
            self.reactorThread = threading.Thread(target=self.reactorThreadLoop)
            self.reactorThread.start()



    def reactorThreadLoop(self):
        try:
            if self.profiler is not None:
                self.profiler.enable()
            while self._isConnected():
                with self.messageProcessor:
                    try:
                        message = self.messageQueue.get(True, GRAPH_UPDATE_TIME)
                    except Queue.Empty:
                        message = None

                    responses = self.messageProcessor.handleIncomingMessage(message)

                    responses += self.messageProcessor.extractPendingMessages()

                    if self.messageProcessor.isDisconnectedFromSharedState():
                        logging.critical("BackendGateway disconnected from SharedState. Exiting.")
                        return

                    for jsonMessage in responses:
                        try:
                            self._on_message(json.dumps(jsonMessage))
                        except:
                            logging.error(
                                "error writing response message: %s\n%s",
                                jsonMessage,
                                traceback.format_exc()
                                )
        except:
            logging.error("err:%s", traceback.format_exc())
        finally:
            if self.profiler is not None:
                self.profiler.disable()

                s = StringIO.StringIO()
                sortby = 'cumulative'
                ps = pstats.Stats(self.profiler, stream=s).sort_stats(sortby)
                ps.print_stats()
                print s.getvalue()


    def close(self):
        with self.lock:
            if not self._isConnected():
                return
            reactorThread = self.reactorThread
            self.reactorThread = None

        reactorThread.join()
        self.messageProcessor.teardown()
        self.messageProcessor = None

    def isConnected(self):
        with self.lock:
            return self._isConnected()

    def send(self, message, callback):
        with self.lock:
            self._raiseIfNotConnected()
            messageId = self.nextMessageId
            self.nextMessageId += 1
            self.messageHandlers[messageId] = callback

            message['messageId'] = messageId

            def encoder(obj):
                if not isinstance(obj, dict) and hasattr(obj, 'toMemoizedJSON'):
                    return obj.toMemoizedJSON()
                return obj

            self.messageQueue.put(json.dumps(message, default=encoder))

    def on(self, event, callback):
        if event in self.events:
            raise ValueError("Event handler for '%s' already exists" % event)
        self.events[event] = callback

    def _isConnected(self):
        return self.reactorThread is not None

    def _raiseIfNotConnected(self):
        if not self._isConnected():
            raise ValueError('Performing I/O on disconnected socket')

    def _triggerEvent(self, event, *args, **kwargs):
        if event in self.events:
            self.events[event](*args, **kwargs)

    def _on_message(self, payload):
        try:
            message = json.loads(payload)
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



