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

import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.distributed.SharedState.Connections.InMemoryChannelFactory as InMemoryChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.native.Json as NativeJson
import ufora.native.CallbackScheduler as CallbackScheduler

IN_MEMORY_HARNESS_PING_INTERVAL = 1.0

class SharedStateTestHarness(object):
    def __init__(self,
            inMemory,
            port = None,
            cachePathOverride = '',
            maxOpenFiles = 256,
            inMemChannelFactoryFactory = None,
            maxLogFileSizeMb = 10,
            pingInterval = None):

        self.inMemory = inMemory
        self.manager = None
        self.callbackScheduler = CallbackScheduler.singletonForTesting()

        if self.inMemory:
            self.manager = SharedStateService.KeyspaceManager(
                10001,
                1,
                cachePathOverride=cachePathOverride,
                pingInterval = IN_MEMORY_HARNESS_PING_INTERVAL if pingInterval is None else pingInterval,
                maxOpenFiles=maxOpenFiles,
                maxLogFileSizeMb=maxLogFileSizeMb
                )

            #although named otherwise InMemoryChannelFactory is actually a factory for a channelFactory
            # or a channelFactoryFactory

            channelFactoryFactory = inMemChannelFactoryFactory if inMemChannelFactoryFactory is not None \
                    else InMemoryChannelFactory.InMemoryChannelFactory

            logging.info(channelFactoryFactory)
            self.channelFactory = channelFactoryFactory(self.callbackScheduler, self.manager)
            self.viewFactory = ViewFactory.ViewFactory(self.channelFactory)
        else:
            class Settings(object):
                callbackScheduler = self.callbackScheduler

            assert port is not None

            self.service = SharedStateService.SharedStateService(
                    self.callbackScheduler,
                    cachePathOverride=cachePathOverride,
                    port=port
                    )

            self.service.startService()
            self.service.blockUntilListening()

            self.viewFactory = ViewFactory.ViewFactory.TcpViewFactory(self.callbackScheduler, "localhost", port)
            #give the thread some time to set up the socket connection


    def teardown(self):
        if not self.inMemory:
            self.service.stopService()
            self.service = None
        else:
            if self.manager:
                self.manager.shutdown()
                self.manager = None
            self.channelFactory.teardown()

    def sendPingAndCompact(self):
        self.manager.check()

    def newView(self):
        view = self.viewFactory.createView()

        if not view.waitConnectTimeout(2.0):
            raise Exception("Failed to connect to SharedState")

        return view

    def subscribeToKeyspace(self, view, spacename):
        keyspace = SharedState.Keyspace("TakeHighestIdKeyType", spacename, 1)

        view.subscribe(
            SharedState.KeyRange(
                keyspace, 0, None, None, True, False
                ),
            True
            )

    def writeToKeyspace(self, view, spacename, key, val):
        keyspace = SharedState.Keyspace("TakeHighestIdKeyType", spacename, 1)

        with SharedState.Transaction(view):
            view[SharedState.Key(keyspace, (key,))] = val

    def getAllKeysFromView(self, view, spacename):
        keyspace = SharedState.Keyspace("TakeHighestIdKeyType", spacename, 1)

        with SharedState.Transaction(view):
            return [x for x in SharedState.iterKeys(view, keyspace)]

    def getAllItemsFromView(self, view, spacename):
        keyspace = SharedState.Keyspace("TakeHighestIdKeyType", spacename, 1)

        with SharedState.Transaction(view):
            return [(x[0], x[1].value()) for x in SharedState.iterItems(view, keyspace)]



