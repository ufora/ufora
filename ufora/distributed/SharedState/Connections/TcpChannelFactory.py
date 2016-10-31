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

import logging
import os
import socket

import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.SharedState.Connections.ChannelFactory as ChannelFactory
import ufora.distributed.SharedState.Exceptions as Exceptions

import ufora.networking.SocketStringChannel as SocketStringChannel

class TcpChannelFactory(ChannelFactory.ChannelFactory):
    def createSocketChannel(self, sock):
        raise NotImplementedError()

    def establishConnection_(self, host, port):
        try:
            logging.debug("Opening TCP channel to: %s:%s", host, port)

            sock = SimpleServer.SimpleServer.connect(host, port)

            logging.debug("TcpChannel: %s ", sock.fileno())

            channel = self.createSocketChannel(sock)

            logging.debug('TcpChannelFactory %s connected: %s:%s', self, host, port)

            return channel
        except socket.error as exc:
            raise Exceptions.SharedStateConnectionError(exc)
        except os.error as exc:
            raise Exceptions.SharedStateConnectionError(exc)



class TcpMessageChannelFactory(TcpChannelFactory):
    def __init__(self, callbackScheduler, host, port):
        self.callbackScheduler = callbackScheduler
        self.host = host
        self.port = port

    def createSocketChannel(self, sock):
        return SharedStateService.createClientSocketMessageChannel(self.callbackScheduler, sock)

    def createChannel(self):
        return self.establishConnection_(self.host, self.port)

    def __str__(self):
        return "TcpMessageChannelFactory(%s,%s)" % (self.host, self.port)


class TcpStringChannelFactory(TcpChannelFactory):
    def __init__(self, callbackScheduler):
        super(TcpStringChannelFactory, self).__init__()
        self.callbackScheduler = callbackScheduler
    def createSocketChannel(self, sock):
        return SocketStringChannel.SocketStringChannel(self.callbackScheduler, sock)

    def createChannel(self, ipEndpoint):
        return self.establishConnection_(*ipEndpoint)

    def __str__(self):
        return "TcpStringChannelFactory"

