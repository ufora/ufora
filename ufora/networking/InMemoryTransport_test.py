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

import unittest
import threading

import ufora.networking.InMemoryTransport as InMemoryTransport
import ufora.native.StringChannel as StringChannelNative

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

class TestInMemoryTransport(unittest.TestCase):
    def setUp(self):
        self.serverChannel, self.clientChannel = StringChannelNative.QueuelikeInMemoryStringChannel(callbackScheduler)
        self.transport = InMemoryTransport.InMemoryTransport(self.clientChannel)

    def connect(self, onLogin):
        deferred = self.transport.connect(('username', 'password'))
        deferred.addCallbacks(onLogin, onLogin)

        loginRequest = self.serverChannel.get()
        self.assertEqual(loginRequest, "CONNECT:username,password")
        self.serverChannel.write("CONNECT:OK,username,user_id,display name,fake_auth_token")

    def disconnect(self):
        self.transport.disconnect()
        disconnectMessage = self.serverChannel.get()
        self.assertEqual(disconnectMessage, 'DISCONNECT')

    def validateLoginResult(self, result):
        self.assertEqual(result['login'], 'username')
        self.assertEqual(result['sharedStateId'], 'user_id')
        self.assertEqual(result['displayName'], 'display name')
        self.assertEqual(result['sharedStateToken'], 'fake_auth_token')

    def test_message_callback_required_to_connect(self):
        self.assertRaisesRegexp(
                AssertionError,
                'onMessageReceived callback must be set before connecting.',
                self.transport.connect,
                ('username', 'password')
                )

    def test_disconnect_callback_required_to_connect(self):
        self.transport.onMessageReceived = lambda message: message
        self.assertRaisesRegexp(
                AssertionError,
                'onDisconnected callback must be set before connecting.',
                self.transport.connect,
                ('username', 'password')
                )

    def test_connect_disconnect(self):
        self.transport.onMessageReceived = lambda message: message
        self.transport.onDisconnected = lambda message: message
        testCompleteEvent = threading.Event()

        def loginComplete(result):
            self.validateLoginResult(result)
            self.disconnect()
            testCompleteEvent.set()

        self.connect(loginComplete)
        self.assertTrue(testCompleteEvent.wait(1))
        self.transport.blockUntilFullyDisconnected()


    def test_reconnect(self):
        self.test_connect_disconnect()
        self.test_connect_disconnect()

    def test_disconnect_message(self):
        self.transport.onMessageReceived = lambda message: message
        testCompleteEvent = threading.Event()

        def onDisconnect():
            testCompleteEvent.set()

        self.transport.onDisconnected = onDisconnect

        def loginComplete(result):
            self.validateLoginResult(result)
            self.serverChannel.write('DISCONNECT')

        self.connect(loginComplete)
        self.assertTrue(testCompleteEvent.wait(1))
        self.transport.blockUntilFullyDisconnected()

    def test_disconnect_message_twice(self):
        self.test_disconnect_message()
        self.test_disconnect_message()

