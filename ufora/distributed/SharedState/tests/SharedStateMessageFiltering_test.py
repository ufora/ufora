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

import unittest
import time
import Queue
import ufora.native.Json as NativeJson
import threading

import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.distributed.SharedState.Connections.FilteredChannelFactory as FilteredChannelFactory
import ufora.util.ManagedThread as ManagedThread
import ufora.native.SharedState as SharedStateNative

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

class MessageFilteringTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_channel_wrappers(self):
        viewChannel, managerChannel = SharedStateNative.InMemoryChannel(callbackScheduler)
        message = SharedState.MessageOut.MinimumIdResponse(0)
        viewChannel.write(message)
        managerChannel.get()

    def filterAllButMinId(self, message, inputChannel, outputChannel):
        return None if message.isMinimumIdResponse() else message

    def test_filtered_channels_noblock(self):
        channelFilter = FilteredChannelFactory.FilteredChannel(callbackScheduler, self.filterAllButMinId)
        try:
            viewChannel, managerChannel = channelFilter.getChannelPair()
            MessageOut = getattr(SharedStateNative, 'SharedState::MessageOut')
            filteredMessage = MessageOut.MinimumIdResponse(0)
            allowedMessage = MessageOut.FlushRequest(0)
            viewChannel.write(filteredMessage)
            viewChannel.write(allowedMessage)

            toGet = [None]
            def tryGet():
                toGet[0] = managerChannel.get()

            t = ManagedThread.ManagedThread(target=tryGet)
            t.start()
            t.join(4)
            self.assertIsNotNone(toGet[0])
        finally:
            channelFilter.teardown()



    def filterMinId(self, message, inputChannel, outputChannel):
        if isinstance(message, SharedState.MessageOut):
            if message.isMinimumIdResponse():
                return None
            if message.isBundle():
                elts = []
                for elt in message.getBundleElements():
                    res = self.filterMinId(elt, inputChannel, outputChannel)
                    if res is not None:
                        elts.append(res)
                return SharedState.MessageOut.Bundle(elts)
        return message

    def noFilter(self, message, inputChannel, outputChannel):
        return message

    def filterInitialize(self, message, inputChannel, outputChannel):
        if isinstance(message, SharedState.MessageIn):
            if message.isInitialize():
                return None
            if message.isBundle():
                elts = []
                for elt in message.getBundleElements():
                    res = self.filterInitialize(elt, inputChannel, outputChannel)
                    if res is not None:
                        elts.append(res)
                return SharedState.MessageIn.Bundle(elts)
        return message

    def test_filtered_channel(self):
        """Verify that message filtering works

        The sender sends a message that is expected to be filtered by FilteredChannel.
        The test verifies that the receiver doesn't get the message
        """
        channelFilter = FilteredChannelFactory.FilteredChannel(callbackScheduler, self.filterMinId)
        try:
            sender, receiver = channelFilter.getChannelPair()
            filteredMessage = SharedState.MessageOut.MinimumIdResponse(0)
            sender.write(filteredMessage)

            toGet = [None]
            def tryGet():
                try:
                    toGet[0] = receiver.get()
                except UserWarning:
                    if channelFilter.stopFlag.is_set():
                        return
                    else:
                        raise

            t = ManagedThread.ManagedThread(target=tryGet)
            t.start()
            t.join(1)
            self.assertIsNone(toGet[0])
        finally:
            channelFilter.teardown()

    def test_shared_state_works(self):
        try:
            def createFilteredChannelFactoryWithNoFilter(callbackScheduler, manager):
                return FilteredChannelFactory.FilteredChannelFactory(callbackScheduler, manager, self.noFilter)

            harness = SharedStateTestHarness.SharedStateTestHarness(
                    True,
                    inMemChannelFactoryFactory=createFilteredChannelFactoryWithNoFilter
                    )
            view = harness.newView()
            self.assertIsNotNone(view.id)
        finally:
            harness.teardown()

    def test_shared_state_hang_on_view_id(self):
        try:
            def createFilteredChannelFactory(callbackScheduler, manager):
                return FilteredChannelFactory.FilteredChannelFactory(callbackScheduler, manager, self.filterInitialize)

            harness = SharedStateTestHarness.SharedStateTestHarness(
                    True,
                    inMemChannelFactoryFactory=createFilteredChannelFactory
                    )
            view = harness.viewFactory.createView()
            def getViewId():
                try:
                    view.id
                except UserWarning:
                    pass
            thread = ManagedThread.ManagedThread(target=getViewId)
            thread.start()
            thread.join(1)
            self.assertTrue(thread.isAlive())
            view.teardown()
            thread.join()
        finally:
            harness.teardown()

    def test_shared_state_disconnect_idle_client(self):
        try:
            def createFilteredChannelFactory(callbackScheduler, manager):
                return FilteredChannelFactory.FilteredChannelFactory(callbackScheduler, manager, self.filterMinId)

            harness = SharedStateTestHarness.SharedStateTestHarness(
                    True,
                    inMemChannelFactoryFactory=createFilteredChannelFactory
                    )
            view = harness.viewFactory.createView()
            view.waitConnect()
            listener = SharedState.Listener(view)
            time.sleep(SharedStateTestHarness.IN_MEMORY_HARNESS_PING_INTERVAL + 1.0)
            listener.get()
            self.assertFalse(listener.isConnected)
        finally:
            view.teardown()
            harness.teardown()




    def test_handles_ping_while_frozen(self):
        allMessagesQueue = Queue.Queue()
        minimumIdResponseQueue = Queue.Queue()
        self.channelPairForId = {}
        self.idForChannelPair = {}

        self.incomingChannelsToBlock = {}
        self.outgoingChannelsToBlock = {}
        self.channelLock = threading.Lock()

        def processMessage(message, inputChannel, outputChannel):
            if message.tag == "Initialize":
                self.channelPairForId[message.asInitialize.clientId] = (inputChannel, outputChannel)
                self.idForChannelPair[(inputChannel, outputChannel)] = message.asInitialize.clientId
            if message.tag == "MinimumIdResponse":
                minimumIdResponseQueue.put((message.asMinimumIdResponse, inputChannel, outputChannel))
            allMessagesQueue.put((message,  inputChannel, outputChannel))

            if (inputChannel, outputChannel) in self.idForChannelPair:
                clientId  = self.idForChannelPair[(inputChannel, outputChannel)]
                if clientId in self.incomingChannelsToBlock:
                    self.incomingChannelsToBlock[clientId].append((message, inputChannel, outputChannel))
                    return None

            elif (outputChannel, inputChannel) in self.idForChannelPair:
                clientId  = self.idForChannelPair[(outputChannel, inputChannel)]

                with self.channelLock:
                    if clientId in self.outgoingChannelsToBlock:
                        self.outgoingChannelsToBlock[clientId].append((message, outputChannel, inputChannel))
                        return None
            return message


        def getMinIds(numChannels):
            self.harness.manager.check()
            tr =  [minimumIdResponseQueue.get()[0].id for ix in range(numChannels)]
            return tr


        def unbundler(message, inputChannel, outputChannel):
            if message.isBundle():
                elts = []
                for elt in message.getBundleElements():
                    res = processMessage(elt, inputChannel, outputChannel)
                    if res is not None:
                        elts.append(res)
                if isinstance(message, SharedState.MessageOut):
                    return SharedState.MessageOut.Bundle(elts)
                else:
                    return SharedState.MessageIn.Bundle(elts)
            return processMessage(message, inputChannel, outputChannel)

        def drainBlockedChannel(view):
            with self.channelLock:
                messagesToSend = self.outgoingChannelsToBlock[view.id]
                del self.outgoingChannelsToBlock[view.id]

            for message, inputChannel, outputChannel in messagesToSend:
                if isinstance(message, SharedState.MessageIn):
                    outputChannel.write(message)
                else:
                    inputChannel.write(message)

        self.harness = None
        v1 = None
        v2 = None

        self.keyspace = NativeJson.Json('testspace')
        self.keyspace2 = NativeJson.Json('testspace2')

        try:
            def createFilteredChannelFactory(callbackScheduler, manager):
                return FilteredChannelFactory.FilteredChannelFactory(callbackScheduler, manager, unbundler)

            self.harness = SharedStateTestHarness.SharedStateTestHarness(
                    True,
                    inMemChannelFactoryFactory=createFilteredChannelFactory,
                    pingInterval = 0xffffffff
                    )

            v1 = self.harness.viewFactory.createView()
            v1.waitConnect()

            v2 = self.harness.viewFactory.createView()
            v2.waitConnect()


            self.harness.subscribeToKeyspace(v1, self.keyspace)
            self.harness.subscribeToKeyspace(v2, self.keyspace)
            self.harness.subscribeToKeyspace(v2, self.keyspace2)

            json = lambda string : NativeJson.Json(string)


            for ix in range(100):
                self.harness.writeToKeyspace(v2, self.keyspace2, json('hello'), json('hello-%s' % ix))

            v1.flush()
            v2.flush()

            getMinIds(2)
            v1.flush()
            v2.flush()



            self.outgoingChannelsToBlock[v1.id] = []
            for ix in range(100):
                self.harness.writeToKeyspace(v1, self.keyspace, json('hello'), json('hello-%s' % ix))

            while len(self.outgoingChannelsToBlock[v1.id]) < 100:
                time.sleep(.1)
            getMinIds(2)

            drainBlockedChannel(v1)

            v2.flush()
            v1.flush() # this may segfault if this test fails

            # test that v1 is still connected. Will throw an exception
            self.harness.writeToKeyspace(v1, self.keyspace, json('hello'), json('hello-%s' % ix))


        finally:
            if v1:
                v1.teardown()
            if v2:
                v2.teardown()
            if self.harness:
                self.harness.teardown()

