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

import ufora.native.StringChannel as StringChannelNative
import ufora.native.SharedState as SharedStateNative
import threading

from ufora.distributed.SharedState.Connections.ChannelFactory import ChannelFactory

class InMemoryChannelFactory(ChannelFactory):
    def __init__(self, callbackScheduler, channelManager):
        self.callbackScheduler = callbackScheduler
        self.channelManager = channelManager
        self.lock = threading.Lock()
        self.channels = []

    def createChannel(self, ipEndpoint = None):
        assert ipEndpoint is None
        viewChannel, managerChannel = SharedStateNative.InMemoryChannel(self.callbackScheduler)
        with self.lock:
            self.channelManager.add(managerChannel)
            self.channels.append(managerChannel)

        return viewChannel

    def disconnectAllChannels(self):
        with self.lock:
            for c in self.channels:
                c.disconnect()
            self.channels = []

    def teardown(self):
        pass


class SerializedChannelFactoryBase(ChannelFactory):
    def __init__(self, callbackScheduler, channelManager, channelGroup):
        self.callbackScheduler = callbackScheduler
        self.channelManager = channelManager
        self.channelGroup = channelGroup

    def createChannel(self, ipEndpoint = None):
        """ipEndpoint is a tuple of the form (host, port)"""
        clientChannel, serverChannel = self.channelType(self.callbackScheduler)
        hostId = ''
        if ipEndpoint is not None:
            hostId = '%s:%s' % ipEndpoint
        self.channelManager.add(serverChannel, self.channelGroup, hostId)
        return clientChannel


class ViewToSerializedChannelFactory(SerializedChannelFactoryBase):
    def __init__(self, callbackScheduler, channelManager, channelGroup):
        super(ViewToSerializedChannelFactory, self).__init__(callbackScheduler, channelManager, channelGroup)
        self.channelType = SharedStateNative.ViewToSerializedChannel

    def createChannel(self, ipEndpoint = None):
        clientChannel, serverChannel = self.channelType(self.callbackScheduler)
        hostId = ''
        if ipEndpoint is not None:
            hostId = '%s:%s' % ipEndpoint
        self.channelManager.add(serverChannel, self.channelGroup, hostId)
        return clientChannel

class SerializedToManagerChannelFactory(SerializedChannelFactoryBase):
    def __init__(self, callbackScheduler, channelManager, channelGroup):
        super(SerializedToManagerChannelFactory, self).__init__(callbackScheduler, channelManager, channelGroup)
        self.channelType = SharedStateNative.SerializedToManagerChannel

    def createChannel(self, ipEndpoint = None):
        clientChannel, serverChannel = self.channelType(self.callbackScheduler)
        self.channelManager.add(serverChannel)
        return clientChannel


class StringChannelFactory(SerializedChannelFactoryBase):
    def __init__(self, callbackScheduler, channelManager, channelGroup):
        super(StringChannelFactory, self).__init__(callbackScheduler, channelManager, channelGroup)
        self.channelType = StringChannelNative.InMemoryStringChannel

