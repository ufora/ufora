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

import threading
import ufora.distributed.SharedState.Connections.InMemoryChannelFactory as InMemoryChannelFactory
import ufora.util.ManagedThread as ManagedThread
import ufora.native.SharedState as SharedStateNative




class FilteredChannelFactory(InMemoryChannelFactory.InMemoryChannelFactory):
    def __init__(self, callbackScheduler, manager, filterFun):
        super(FilteredChannelFactory, self).__init__(callbackScheduler, manager)
        self.callbackScheduler = callbackScheduler
        self.managedChannels = []
        self.filterFun = filterFun

    def createChannel(self, ipEndpoint=None):
        channel = FilteredChannel(self.callbackScheduler, self.filterFun)
        self.managedChannels.append(channel)
        viewChannel, managerChannel =  channel.getChannelPair()
        self.channelManager.add(managerChannel)
        return viewChannel

    def teardown(self):
        super(FilteredChannelFactory, self).teardown()
        for channel in self.managedChannels:
            channel.teardown()
        self.managedChannels = []

class FilteredChannel(object):
    def __init__(self, callbackScheduler, filterFun) :
        self.filterFun = filterFun
        self.callbackScheduler= callbackScheduler
        self.viewFacingViewChannel, self.filterFacingManagerChannel = SharedStateNative.InMemoryChannel(self.callbackScheduler)
        self.filterFacingViewChannel, self.managerFacingManagerChannel = SharedStateNative.InMemoryChannel(self.callbackScheduler)
        self.stopFlag = threading.Event()

        self.channelPumpThreads = []
        self.channelPumpThreads.append(
                ManagedThread.ManagedThread(
                    target=self.filteredChannelPump,
                    args=(self.filterFacingManagerChannel, self.filterFacingViewChannel)
                    )
                )
        self.channelPumpThreads.append(
                ManagedThread.ManagedThread(
                    target=self.filteredChannelPump,
                    args=(self.filterFacingViewChannel, self.filterFacingManagerChannel)
                    )
                )
        for thread in self.channelPumpThreads:
            thread.start()

    def teardown(self):
        self.stopFlag.set()
        self.viewFacingViewChannel.disconnect()
        self.filterFacingManagerChannel.disconnect()
        self.managerFacingManagerChannel.disconnect()
        self.filterFacingViewChannel.disconnect()
        for thread in self.channelPumpThreads:
            thread.join()

    def getChannelPair(self):
        return self.viewFacingViewChannel, self.managerFacingManagerChannel

    def filteredChannelPump(self, inputChannel, outputChannel):
        channelToDisconnect = None
        while not self.stopFlag.is_set():
            try:
                channelToDisconnect = outputChannel
                message = self.filterFun(inputChannel.get(), inputChannel, outputChannel)
                if message is not None:
                    channelToDisconnect = inputChannel
                    outputChannel.write(message)
            except UserWarning:
                if not self.stopFlag.is_set():
                    channelToDisconnect.disconnect()
                return


