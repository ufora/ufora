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
import ufora.config.Setup as Setup
import ufora.networking.ChannelListener as ChannelListener
import ufora.util.ManagedThread as ManagedThread
import ufora.distributed.SharedState.Connections.TcpChannelFactory as TcpChannelFactory
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

class ChannelEchoServer(ChannelListener.ChannelListener):
    def __init__(self, port, echoMultiplier=1, sizeMultiplier=1):
        super(ChannelEchoServer, self).__init__(callbackScheduler, port)
        self._echoMultiplier = echoMultiplier
        self._sizeMultiplier = sizeMultiplier
        self.channels = []
        self.threads = []
        self._stopFlag = threading.Event()
        self.channelConnectCallback = self._channelConnectCallback

    def _channelConnectCallback(self, channel):
        channel = channel.makeQueuelike(callbackScheduler)

        t = ManagedThread.ManagedThread(target=self._echoLoop, args=(channel,))
        t.start()
        self.threads.append(t)
        self.channels.append(t)

    def teardown(self):
        super(ChannelEchoServer, self).stop()
        self._stopFlag.set()
        for t in self.threads:
            t.join()

    def _echoLoop(self, channel):
        while not self._stopFlag.is_set():
            try:
                toEcho = channel.get()
            except UserWarning:
                return
            try:
                if self._sizeMultiplier > 1:
                    toEcho = toEcho * self._sizeMultiplier
                for i in range(self._echoMultiplier):
                    channel.write(toEcho)
            except UserWarning:
                return



class ChannelFactoryTest(unittest.TestCase):
    def setUp(self):
        self.port = Setup.config().testPort

    def test_socket_listener(self):
        server = ChannelEchoServer(self.port)
        try:
            thread = ManagedThread.ManagedThread(target=server.start)
            thread.start()
            server.blockUntilReady()
            stringChannelFactory = TcpChannelFactory.TcpStringChannelFactory(callbackScheduler)
            channel = stringChannelFactory.createChannel(
                        ('localhost', self.port)
                        )

            channel = channel.makeQueuelike(callbackScheduler)

            toSend = "Hi There!"
            channel.write(toSend)
            self.assertEquals(toSend, channel.get())

        finally:
            try:
                server.teardown()
            except UserWarning:
                pass
            thread.join()



    def test_socket_channel_shutdown(self):
        done = threading.Event()
        listener = ChannelListener.SocketListener(self.port)
        listener.registerConnectCallback(lambda sock, address : done.set())

        try:
            thread = ManagedThread.ManagedThread(target=listener.start)
            thread.start()
            listener.blockUntilReady()

            TcpChannelFactory.TcpStringChannelFactory(callbackScheduler).createChannel(('localhost', self.port))

            self.assertTrue(done.wait(2))

        finally:
            listener.stop()
            thread.join()

