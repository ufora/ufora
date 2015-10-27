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

import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import ufora.networking.SocketStringChannel as SocketStringChannel
import ufora.util.ManagedThread as ManagedThread
import threading
import logging
import traceback

class SocketListener(object):
    def __init__(self, port, portScanIncrement=0):
        assert isinstance(port, int)
        assert isinstance(portScanIncrement, int)

        self.requestedPort = port
        self.port = port
        self.portScanIncrement = portScanIncrement
        self.socketServer = SimpleServer.SimpleServer(self.port)
        self.boundEvent_ = threading.Event()
        self.tornDown = False
        self.onPortBound = None
        self.socketConnectCallback = None
        self.socketServer._onConnect = self.onSocketConnect
        self.listenerThread = ManagedThread.ManagedThread(target=self.socketServer.start)

    def __str__(self):
        return "SocketListener(port=%d, portScanIncrement=%d)" % (self.port, self.portScanIncrement)

    def registerConnectCallback(self, callback):
        assert callable(callback)
        self.socketConnectCallback = callback


    def start(self):
        assert not self.tornDown
        logging.info("Starting %s", str(self))
        while not self.boundEvent_.isSet():
            try:
                self.socketServer.bindListener(self.port)
                try:
                    self.onPortBound_()
                except:
                    logging.critical(
                        "ChannelListener.onPortBound_ fired an exception: %s",
                        traceback.format_exc()
                        )
                    raise
                self.boundEvent_.set()
            except:
                if self.portScanIncrement == 0:
                    raise

                logging.info(
                    "ChannelListener tried to bind to port %d but failed. Trying port %d now.",
                    self.port,
                    self.port + self.portScanIncrement
                    )
                self.port += self.portScanIncrement
                logging.info("New port is %d", self.port)
        self.listenerThread.start()

    def stop(self):
        self.boundEvent_.set()
        self.tornDown = True
        self.socketServer.stop()
        if self.listenerThread.isAlive():
            self.listenerThread.join()

    def onSocketConnect(self, sock, address):
        if self.socketConnectCallback is not None:
            self.socketConnectCallback(sock, address)
        else:
            assert False, "onSocketConnect must be overridden or rebound to another function"

    def onPortBound_(self):
        if self.onPortBound is not None:
            self.onPortBound(self.requestedPort, self.port)

    def blockUntilReady(self):
        self.boundEvent_.wait()

class ChannelListener(SocketListener):
    '''
    Listens for incoming channel connections
    '''
    def __init__(self, callbackScheduler, port, portScanIncrement=0):
        SocketListener.__init__(self, port, portScanIncrement=portScanIncrement)
        self.callbackScheduler = callbackScheduler
        self.channelConnectCallbackLock = threading.Lock()
        self.channelConnectCallback = None
        #connected channels that were given before a callback was installed
        self.pendingChannelConnections = []
        self.channelsToTeardown = set()

    def __str__(self):
        return "ChannelListener(port=%d, portScanIncrement=%d)" % (self.port, self.portScanIncrement)

    def onSocketConnect(self, sock, address):
        logging.info("Accepted socket from %s", address)
        channel = self.createSocketChannel(sock).makeQueuelike(self.callbackScheduler)
        assert not self.tornDown
        self.channelsToTeardown.add(channel)

        with self.channelConnectCallbackLock:
            if self.channelConnectCallback is not None:
                callCallback = True
            else:
                callCallback = False
                self.pendingChannelConnections.append(channel)

        #note that we are careful not to call the callback under a lock. The lock is
        #only there to ensure that we don't add a channel to the pending queue while
        #another thread is adding the callback
        if callCallback:
            self.channelConnectCallback(channel)

    def registerConnectCallback(self, callbackFun):
        assert callbackFun is not None
        with self.channelConnectCallbackLock:
            assert self.channelConnectCallback is None

            self.channelConnectCallback = callbackFun

            pending = self.pendingChannelConnections
            self.pendingChannelConnections = None # Set to None to ensure we get an exception is anyone tries to append

        for channel in pending:
            self.channelConnectCallback(pending)

    def registerChannelDisconnected(self, channel):
        '''
        Called when a channel is disconnected outside of thie class
        '''
        if channel in self.channelsToTeardown:
            self.channelsToTeardown.remove(channel)

    def createSocketChannel(self, sock):
        return SocketStringChannel.SocketStringChannel(self.callbackScheduler, sock)

    def stop(self):
        SocketListener.stop(self)
        for channel in self.channelsToTeardown:
            channel.disconnect()

