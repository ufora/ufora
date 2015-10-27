#!/usr/bin/env python

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
import logging
import os
import pickle
import socket
import struct
import sys
import traceback

import ufora.BackendGateway.SubscribableWebObjects.ConnectionHandler as ConnectionHandler
import ufora.FORA.python.FORA as FORA
import ufora.config.Mainline as Mainline
import ufora.config.Setup as Setup
import ufora.distributed.SharedState.Connections.TcpChannelFactory as TcpChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.networking.SocketStringChannel as SocketStringChannel
import ufora.util.Unicode as Unicode


class BackendGatewayRequestHandler(object):
    def __init__(self,
                 socketFd,
                 sharedStateAddress):
        self.socketFd = socketFd
        self.callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()

        self.scheduler = self.callbackSchedulerFactory.createScheduler(
            "BackendGatewayRequestHandler",
            1
            )

        sharedStateHost, sharedStatePort = sharedStateAddress.split(':')
        sharedStateViewFactory = ViewFactory.ViewFactory.TcpViewFactory(
            self.callbackSchedulerFactory.createScheduler('SharedState', 1),
            sharedStateHost,
            int(sharedStatePort),
            ViewFactory.TEST_KEY_ALL_KEYSPACE_ACCESS_AUTH_TOKEN
            )

        self.subscribableHandler = ConnectionHandler.ConnectionHandler(
            self.scheduler,
            sharedStateViewFactory,
            lambda: TcpChannelFactory.TcpStringChannelFactory(self.scheduler)
            )
        self.sock = socket.fromfd(socketFd, socket.AF_INET, socket.SOCK_STREAM)


    def serviceRequest(self, channel):
        logging.info("processing request")
        try:
            msg = channel.get()
            request = json.loads(msg, object_hook=Unicode.convertToStringRecursively)
            logging.info(
                "handler %s processing request: %s",
                os.getpid(),
                json.dumps(request, indent=2)
                )

            self.subscribableHandler.serviceIncomingChannel(request, channel)
        except:
            logging.error(
                "BackendGateway handled fatal exception in socket loop:\n%s",
                traceback.format_exc()
                )
        finally:
            try:
                channel.disconnect()
            except:
                logging.warn("Error trying to disconnect channel: %s", traceback.format_exc())

            logging.info("BackendGateway socket loop exiting")


    def handle(self):
        logging.info("all file descriptors closed")
        callbackScheduler = \
            CallbackScheduler.createSimpleCallbackSchedulerFactory().createScheduler(
                "BackendGatewayService",
                1
                )


        channel = SocketStringChannel.SocketStringChannel(
            callbackScheduler,
            self.sock).makeQueuelike(callbackScheduler)
        logging.info("channel connected")

        self.serviceRequest(channel)
        logging.info("Killing self!")

def main(*args):
    Setup.config().configureLoggingForBackgroundProgram()
    try:
        dataLen = struct.unpack('I', sys.stdin.read(struct.calcsize('I')))[0]
        data = sys.stdin.read(dataLen)

        connectionData = pickle.loads(data)

        maxFD = os.sysconf("SC_OPEN_MAX")
        for fd in range(3, maxFD):
            if fd != connectionData['socketFd']:
                try:
                    os.close(fd)
                except:
                    pass

        handler = BackendGatewayRequestHandler(
            connectionData['socketFd'],
            connectionData['sharedStateAddress']
        )

        handler.handle()
    finally:
        sys.stderr.write(traceback.format_exc())
        sys.stderr.write("closing connection handler\n")
        sys.stderr.flush()
    return 0


if __name__ == "__main__":
    Mainline.UserFacingMainline(main, sys.argv, [FORA])


