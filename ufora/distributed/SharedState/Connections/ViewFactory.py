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
import logging

import ufora.config.Setup as Setup
import ufora.distributed.util.common as common

import ufora.native.SharedState as SharedStateNative

from ufora.distributed.SharedState.Connections.TcpChannelFactory import TcpMessageChannelFactory
from ufora.distributed.SharedState.Exceptions import SharedStateConnectionError
from ufora.distributed.SharedState.Exceptions import SharedStateAuthorizationError

import ufora.util.ThreadLocalStack as ThreadLocalStack

#jsonWebToken that authorizes all-keyspace access assuming that the hmac key is the empty string
EMPTY_KEY_ALL_KEYSPACE_ACCESS_AUTH_TOKEN = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ1Zm9yYSIsImV4cCI6MTM1MjkyODA0NSwiaWF0Ijo' +
    'xMzUyOTI3NzQ1LCJhdWQiOiJ1cm46dWZvcmE6c2VydmljZXM6c2hhcmVkc3RhdGUiLCJwcm4iOiJ0ZXN0IiwianR' +
    'pIjoiNThjZjgyYzYtNzRjZi00ZjY1LTliODktNDNhM2NiYTEzODlmIiwiYXV0aG9yaXphdGlvbnMiOlt7ImFjY2V' +
    'zcyI6InJ3IiwicHJlZml4IjoiIn1dfQ.ZlvMNT8C8Iwh7NpMclzU9-XH_NOnc-5fHV-jsqCdmm0'
    )

#jsonWebToken that authorizes all-keyspace access using the default hmac key from Config.py
TEST_KEY_ALL_KEYSPACE_ACCESS_AUTH_TOKEN = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJ1Zm9yYSIsImV4cCI6MTM1MzAxOTI1NywiaWF0Ijo' +
    'xMzUzMDE4OTU3LCJhdWQiOiJ1cm46dWZvcmE6c2VydmljZXM6c2hhcmVkc3RhdGUiLCJwcm4iOiJ0ZXN0IiwianR' +
    'pIjoiOGNmMmMwYmItOWZhOS00MGM2LWJjNTktYTBmMmRhMmYzOTBjIiwiYXV0aG9yaXphdGlvbnMiOlt7ImFjY2V' +
    'zcyI6InJ3IiwicHJlZml4IjoiIn0seyJhY2Nlc3MiOiJyIiwicHJlZml4IjoicHVibGljOjoifSx7ImFjY2VzcyI' +
    '6InJ3IiwicHJlZml4IjoicHVibGljOjp3cml0ZWFibGU6OiJ9LHsiYWNjZXNzIjoiciIsInByZWZpeCI6Il9fQ0x' +
    'JRU5UX0lORk9fU1BBQ0VfXyJ9XX0.JNoCVv5-wFm7e5ZDBD-GejiMzunnfhMi1AzTeSGw41k'
    )

class ViewFactory(ThreadLocalStack.ThreadLocalStackPushable):
    def __init__(self, channelFactory, accessToken=None):
        ThreadLocalStack.ThreadLocalStackPushable.__init__(self)
        self.channelFactory = channelFactory
        self.enableDebugPrint = False
        self.accessToken = accessToken

    def __str__(self):
        return "SharedStateViewFactory(%s)" % (self.channelFactory)

    def createView(self, friendlyName = None, retrySeconds = None, numRetries = 4.0, authorize = True):
        view = None
        t0 = time.time()
        while view is None:
            try:
                view = self.createView_(friendlyName, authorize)
            except (SharedStateConnectionError, common.SocketException):
                if not ViewFactory.waitForRetry_(t0, retrySeconds, numRetries):
                    raise

        return view

    @staticmethod
    def TcpViewFactory(callbackScheduler, address = None, port = None, accessToken = None):
        if address is None:
            raise ValueError("address cannot be None")

        if port is None:
            port = Setup.config().sharedStatePort

        channelFactory = TcpMessageChannelFactory(callbackScheduler, address, port)
        return ViewFactory(channelFactory, accessToken)

    def createView_(self, friendlyName, authorize):
        view = SharedStateNative.createView(self.enableDebugPrint)
        channel = self.channelFactory.createChannel()
        view.add(channel)

        if authorize:
            logging.info("Authorizing view")
            if not view.sendAuthorizationMessage(
                    self.accessToken or TEST_KEY_ALL_KEYSPACE_ACCESS_AUTH_TOKEN,
                    3.0
                    ):
                raise SharedStateAuthorizationError()

        return view

    @staticmethod
    def waitForRetry_(startTime, retrySeconds, numRetries):
        if retrySeconds is not None and time.time() - startTime < retrySeconds:
            time.sleep(retrySeconds / numRetries)
            return True
        return False

