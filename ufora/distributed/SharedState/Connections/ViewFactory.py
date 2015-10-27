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

import ufora.config.Setup as Setup
import ufora.distributed.util.common as common

import ufora.native.SharedState as SharedStateNative

from ufora.distributed.SharedState.Connections.TcpChannelFactory import TcpMessageChannelFactory
from ufora.distributed.SharedState.Exceptions import SharedStateConnectionError

import ufora.util.ThreadLocalStack as ThreadLocalStack

class ViewFactory(ThreadLocalStack.ThreadLocalStackPushable):
    def __init__(self, channelFactory):
        ThreadLocalStack.ThreadLocalStackPushable.__init__(self)
        self.channelFactory = channelFactory
        self.enableDebugPrint = False

    def __str__(self):
        return "SharedStateViewFactory(%s)" % (self.channelFactory)

    def createView(self,
                   friendlyName=None,
                   retrySeconds=None,
                   numRetries=4.0):
        view = None
        t0 = time.time()
        while view is None:
            try:
                view = self.createView_(friendlyName)
            except (SharedStateConnectionError, common.SocketException):
                if not ViewFactory.waitForRetry_(t0, retrySeconds, numRetries):
                    raise

        return view

    @staticmethod
    def TcpViewFactory(callbackScheduler, address=None, port=None):
        if address is None:
            raise ValueError("address cannot be None")

        if port is None:
            port = Setup.config().sharedStatePort

        channelFactory = TcpMessageChannelFactory(callbackScheduler, address, port)
        return ViewFactory(channelFactory)

    def createView_(self, friendlyName):
        view = SharedStateNative.createView(self.enableDebugPrint)
        channel = self.channelFactory.createChannel()
        view.add(channel)

        return view

    @staticmethod
    def waitForRetry_(startTime, retrySeconds, numRetries):
        if retrySeconds is not None and time.time() - startTime < retrySeconds:
            time.sleep(retrySeconds / numRetries)
            return True
        return False

