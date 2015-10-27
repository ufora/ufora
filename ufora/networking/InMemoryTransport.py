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

import threading
import zope.interface
import ufora.networking.Transport as Transport
import ufora.util.ManagedThread as ManagedThread
import ufora.util.Deferred as Deferred


class InMemoryTransport(object):
    zope.interface.implements(Transport.Transport)

    ConnectMessage = 'CONNECT:'
    LogMessage = 'LOG:'
    DisconnectMessage = 'DISCONNECT'

    def __init__(self, channel):
        self.channel = channel
        self.onMessageReceived = None
        self.onDisconnected = None
        self.inputThread = None
        self.isShuttingDown = False

    def connect(self, credentials):
        assert self.onMessageReceived is not None, \
               "onMessageReceived callback must be set before connecting."
        assert self.onDisconnected is not None, \
                "onDisconnected callback must be set before connecting."
        assert not self.isInInputThread(), \
                "connect was called on an already connected transport."

        deferred = Deferred.Deferred()
        self.startInputLoop(deferred)
        if credentials is not None:
            self.channel.write('CONNECT:%s,%s' % credentials)
        return deferred

    def startInputLoop(self, deferred):
        assert self.inputThread is None or not self.inputThread.is_alive()
        self.inputThread = ManagedThread.ManagedThread(target=self.inputLoop, args=(deferred,))
        self.inputThread.start()

    def send(self, content):
        self.channel.write(content)

    def disconnect(self):
        self.isShuttingDown = True
        self.channel.write(InMemoryTransport.DisconnectMessage)

        if not self.isInInputThread():
            self.blockUntilFullyDisconnected()

    def blockUntilFullyDisconnected(self):
        self.inputThread.join()

    def isInInputThread(self):
        return self.inputThread is not None and \
                threading.currentThread().ident == self.inputThread.ident

    def inputLoop(self, connectDeferred):
        try:
            if connectDeferred and not self.waitForConnection(connectDeferred):
                return

            # this call doesn't return until the transport is shut down or gets disconnected
            self.processIncomingMessages()
        finally:
            self.isShuttingDown = False

    def processIncomingMessages(self):
        while not self.isShuttingDown:
            message = self.channel.get()
            if message == InMemoryTransport.DisconnectMessage:
                self.onDisconnected()
                return

            try:
                self.onMessageReceived(message)
            except TypeError as e:
                print 'Error decoding message: %s\nMessage: %s' % (e, message)

    def waitForConnection(self, connectDeferred):
        message = None
        while True:
            message = self.channel.get()
            if message.startswith(InMemoryTransport.ConnectMessage):
                break

        result = message[len(InMemoryTransport.ConnectMessage):].split(',')
        if result[0] == 'OK':
            connectDeferred.callback({
                'login' : result[1],
                'sharedStateId': result[2],
                'displayName': result[3],
                'sharedStateToken' : result[4]
                })
            return True
        else:
            connectDeferred.errback('Failed to connect')
            return False


