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

import time
import unittest
import logging
import threading
import ufora.config.Setup as Setup
import ufora.distributed.util.common as common
import ufora.util.ManagedThread as ManagedThread
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import ufora.native.CallbackScheduler as CallbackScheduler

callbackScheduler = CallbackScheduler.singletonForTesting()

class TestServer(SimpleServer.SimpleServer):
    def __init__(self, port, connectFun):
        super(TestServer, self).__init__(port)
        self._onConnect = connectFun



class TestSocketChannel(unittest.TestCase):
    def setUp(self):
        logging.info("TestSocketChannel setting up")
        self.port = Setup.config().testPort
        self.serverChannel = None
        self.server = None
        self.serverChannelEvent = threading.Event()
        self.tries = 0
        self.server = TestServer(self.port, self.onConnect)
        self.serverThread = ManagedThread.ManagedThread(target=self.server.start)
        self.serverThread.start()
        self.server.blockUntilListening()
        logging.info("Server thread is listening")



    def connectToServer(self):
        sock = SimpleServer.SimpleServer.connect('localhost', self.port)
        return SharedStateService.createClientSocketMessageChannel(callbackScheduler, sock)


    def onConnect(self, sock, address):
        channel = SharedStateService.createServerSocketChannel(callbackScheduler, sock)
        channel.write(SharedState.MessageIn.MinimumId(0,0))
        self.serverChannel = channel
        self.serverChannelEvent.set()


    def tearDown(self):
        logging.info("TestSocketChannel tearing down")
        self.server.stop()

        self.serverThread.join()
        self.serverThread.join(5.0)
        assert not self.serverThread.isAlive()

        logging.info("TestSocketChannel torn down")

    def getChannel(self, timeout):
        channel = None
        startTime = time.time()
        while channel is None:
            try:
                channel = self.connectToServer()
                return channel
            except common.SocketException:
                if time.time() > startTime + timeout:
                    raise
                time.sleep(.1)




    def test_sever(self):
        for ix in range(200):
            if ix % 10 == 0:
                logging.info('Test iteration is %s', ix)

            t0 = time.time()
            self.serverChannelEvent.clear()
            channel = self.getChannel(30)
            timeElapsed = time.time() - t0

            if timeElapsed > .1:
                logging.warn('Fetching channel took %s', timeElapsed)

            channel.get()
            channel.disconnect()
            self.serverChannelEvent.wait(30.0)
            assert self.serverChannelEvent.is_set()
            self.serverChannel.disconnect()

