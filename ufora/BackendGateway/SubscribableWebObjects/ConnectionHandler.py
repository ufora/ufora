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
import threading
import traceback
import time

import ufora.BackendGateway.SubscribableWebObjects.MessageProcessor as MessageProcessor

import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines
import ufora.cumulus.distributed.CumulusGatewayRemote as CumulusGatewayRemote
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway

GRAPH_UPDATE_TIME = .1

class ConnectionHandler:
    """ConnectionHandler - adapts the MessageProcessor for use with TCP channels."""
    def __init__(self, callbackScheduler, sharedStateViewFactory, channelFactoryFactory):
        self.callbackScheduler = callbackScheduler
        self.sharedStateViewFactory = sharedStateViewFactory
        self.channelFactoryFactory = channelFactoryFactory

        self.lock = threading.Lock()
        self.activeCount = 0

    def stopService(self):
        pass

    def serviceIncomingChannel(self, jsonRequest, channel):
        logging.info("Initiating ConnectionHandler: %s", jsonRequest)
        t0 = time.time()

        def createCumulusComputedValueGateway():
            def createCumulusGateway(callbackScheduler, vdm):
                result = CumulusGatewayRemote.RemoteGateway(
                    callbackScheduler,
                    vdm,
                    self.channelFactoryFactory(),
                    CumulusActiveMachines.CumulusActiveMachines(self.sharedStateViewFactory),
                    self.sharedStateViewFactory
                    )
                logging.info("Returing %s as createCumulusGateway", result)
                return result

            return ComputedValueGateway.CumulusComputedValueGateway(
                self.callbackScheduler.getFactory(),
                self.callbackScheduler,
                createCumulusGateway
                )

        messageProcessor = MessageProcessor.MessageProcessor(
            self.callbackScheduler,
            createCumulusComputedValueGateway
            )

        logging.info("Initialized MessageProcessor in %s seconds", time.time() - t0)

        try:
            with self.lock:
                self.activeCount += 1
                logging.info("New Connection. Total active connections = %s", self.activeCount)

            with messageProcessor:
                while True:
                    message = channel.getTimeout(GRAPH_UPDATE_TIME)
                    responses = messageProcessor.handleIncomingMessage(message)
                    responses += messageProcessor.extractPendingMessages()

                    for jsonMessage in responses:
                        try:
                            channel.write(json.dumps(jsonMessage))
                        except:
                            logging.error(
                                "error writing response message: %s\n%s",
                                jsonMessage,
                                traceback.format_exc()
                                )
        except MessageProcessor.MalformedMessageException as e:
            logging.info("MalformedMessage: %s\n%s", e.message, traceback.format_exc())
            channel.disconnect()
        except:
            logging.info("err:%s", traceback.format_exc())
        finally:
            with self.lock:
                self.activeCount -= 1
                logging.info("Lost a connection. Total active connections = %s", self.activeCount)

            messageProcessor.teardown()



