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
import time
import threading

import ufora.networking.MultiChannelListener as MultiChannelListener
import ufora.distributed.SharedState.Connections.TcpChannelFactory as TcpChannelFactory
import ufora.distributed.util.common as common

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

class MultiChannelListenerTest(unittest.TestCase):
    def setUp(self):
        self.defaultGroupId = 42
        self.ports = [54321, 53421, 52431]
        self.connectionCounts = {}
        self.multiChannelListener = MultiChannelListener.MultiChannelListener(callbackScheduler, self.ports)
        self.channelFactory = TcpChannelFactory.TcpStringChannelFactory(callbackScheduler)

    def tearDown(self):
        self.multiChannelListener.stop()

    def createChannel(self, port):
        t0 = time.time()
        lastException = None
        while t0 + 60 > time.time():
            try:
                return self.channelFactory.createChannel(('localhost', port))
            except common.SocketException as e:
                lastException = e

            time.sleep(0.01)

        assert lastException is not None
        raise lastException

    def startListener(self):
        self.multiChannelListener.start(wait=True)
        self.connectionCounts = { ix: 0 for ix in range(len(self.ports))}



    def noopCompletionCallback(self, channels, groupId):
        self.assertEqual(groupId, self.defaultGroupId)

    def noopConnectionCallback(self, portIndex, channel):
        self.multiChannelListener.setGroupIdForAcceptedChannel(
            channel,
            self.defaultGroupId + self.connectionCounts[portIndex]
            )
        self.connectionCounts[portIndex] += 1

    def test_init(self):
        self.assertEqual(len(self.multiChannelListener.listeners), len(self.ports))

    def test_str(self):
        self.assertEqual(
            str(self.multiChannelListener),
            'MultiChannelListener(%s)' % ', '.join([str(p) for p in self.ports])
        )

    def test_start_stop(self):
        self.multiChannelListener.registerConnectCallbackForAllPorts(self.noopConnectionCallback)
        self.multiChannelListener.registerConnectionCompleteCallback(self.noopCompletionCallback)
        self.startListener()
        self.multiChannelListener.stop()

    def test_register_callback_for_missing_port(self):
        with self.assertRaises(Exception):
            self.multiChannelListener.registerConnectCallbackForPort(780, self.noopConnectionCallback)

    def test_register_callback_for_port(self):
        callbackFired = threading.Event()

        def onConnection(portIndex, channel):
            self.assertEqual(portIndex, 0)
            self.assertIsNotNone(channel)
            callbackFired.set()
            return 1  # return some channelGroupID

        self.multiChannelListener.registerConnectCallbackForPort(0, onConnection)
        for i in range(1, len(self.ports)):
            self.multiChannelListener.registerConnectCallbackForPort(i, self.noopConnectionCallback)
        self.multiChannelListener.registerConnectionCompleteCallback(self.noopCompletionCallback)
        self.startListener()

        channel = self.createChannel(self.multiChannelListener.listeners[0].port)
        self.assertIsNotNone(channel)

        self.assertTrue(callbackFired.wait(0.1))
        channel.disconnect()

    def test_connection_completion(self):
        callbackFired = threading.Event()

        def onCompletion(channels, groupId):
            self.assertEqual(len(channels), len(self.ports))
            self.assertEqual(groupId, self.defaultGroupId)
            #for port in self.ports:
                #self.assertIn(port, channels)
            callbackFired.set()

        self.multiChannelListener.registerConnectionCompleteCallback(onCompletion)
        self.multiChannelListener.registerConnectCallbackForAllPorts(self.noopConnectionCallback)
        self.startListener()

        self.multiChannelListener.blockUntilReady()

        clients = [self.createChannel(listener.port) for listener in self.multiChannelListener.listeners]
        self.assertNotIn(None, clients)

        self.assertTrue(callbackFired.wait(0.1))
        for client in clients:
            client.disconnect()

    def test_multiple_channel_groups(self):
        done = threading.Event()
        seenChannels = {ix: [] for ix in range(len(self.ports))}
        remainingGroups = [3]

        def onConnection(portIndex, channel):
            seenChannels[portIndex].append(channel)
            self.multiChannelListener.setGroupIdForAcceptedChannel(channel, len(seenChannels[portIndex]))

        def onCompletion(channels, groupId):
            remainingGroups[0] -= 1
            if (remainingGroups[0] == 0):
                done.set()

        self.multiChannelListener.registerConnectCallbackForAllPorts(onConnection)
        self.multiChannelListener.registerConnectionCompleteCallback(onCompletion)
        self.startListener()

        clients = {listener.index: [self.createChannel(listener.port) for i in range(remainingGroups[0])] for listener in self.multiChannelListener.listeners}

        self.assertTrue(done.wait(0.1))
        for channels in clients.itervalues():
            for channel in channels:
                channel.disconnect()

    def test_orphan_channel_group(self):
        def onCompletion(channels, groupId):
            # should not be called
            self.assertTrue(False)

        groupCompletionTimeout = 0.01
        self.multiChannelListener.GROUP_COMPLETION_TIMEOUT_IN_SECONDS = groupCompletionTimeout
        self.multiChannelListener.registerConnectCallbackForAllPorts(self.noopConnectionCallback)
        self.multiChannelListener.registerConnectionCompleteCallback(onCompletion)
        self.startListener()

        clients = [self.createChannel(self.multiChannelListener.ports[i]) for i in range(1, len(self.ports))]

        # Waiting long enough for the MultiChannelListener to time out this
        # group
        time.sleep(groupCompletionTimeout * 2)

        # initiate another connection to trigger garbage-collection in
        # ChannelListener
        clients.append(self.createChannel(self.multiChannelListener.ports[1]))

        # This should not result in a completed connection because the
        # connection group should have timed out by now
        clients.append(self.createChannel(self.multiChannelListener.ports[0]))
        time.sleep(groupCompletionTimeout)

    def test_accept_timeout(self):
        def onConnection(portIndex, channel):
            pass

        acceptTimeout = 0.01
        self.multiChannelListener.ACCEPT_TIMEOUT_IN_SECONDS = acceptTimeout
        self.multiChannelListener.registerConnectCallbackForAllPorts(onConnection)
        self.multiChannelListener.registerConnectionCompleteCallback(self.noopCompletionCallback)
        self.startListener()

        channels = [self.createChannel(self.multiChannelListener.listeners[0].port).makeQueuelike(callbackScheduler)]

        #wait a sufficient multiple of the timeout that we can be assured that we are not going to
        #be able to connect
        time.sleep(acceptTimeout * 5.0)
        channels.append(self.createChannel(self.multiChannelListener.listeners[0].port))

        with self.assertRaises(UserWarning):
            #this should throw an exception: since we're connecting after the timeout the channel
            #is already disconnected. If this operation does not throw, then the test has failed.
            channels[0].getTimeout(1.0)

        for channel in channels:
            channel.disconnect()

