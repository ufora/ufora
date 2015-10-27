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
import ufora.util.ManagedThread as ManagedThread
import ufora.networking.DemuxedTransport as DemuxedTransport
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory

from ufora.networking.ChannelDemuxer import ChannelDemuxer
from ufora.util.Deferred import FakeDeferred



class Client(object):
    def __init__(self, callbackScheduler, channel):
        self.channel = channel.makeQueuelike(callbackScheduler)
        self.channelGroup = ''
        self.hostId = ''
        self.outgoingSequenceNumber = 0

    def write(self, message):
        self.channel.write(message)

    def disconnect(self):
        self.channel.disconnect()

    def get(self):
        return self.channel.get()

    def getTimeout(self, timeout):
        return self.channel.getTimeout(timeout)

class InMemoryDemuxedTransport(DemuxedTransport.DemuxedTransport):
    '''
    A transport which demuxes and uses multiple in-memory channels to communicate with the in-memory cluster.
    '''
    def __init__(self, callbackScheduler, sharedStateChannelFactory, cumulusChannelFactory):
        super(InMemoryDemuxedTransport, self).__init__()
        self.callbackScheduler = callbackScheduler
        self.sharedStateChannelFactory = sharedStateChannelFactory
        self.cumulusChannelFactory = cumulusChannelFactory

        self.lock = threading.RLock()
        self.channelThreads = {}
        self.shouldStop = False

    def send(self, encodedMessage):
        message = ChannelDemuxer.decodeMessage(encodedMessage)

        client = self._clientForMessage(message)

        try:
            client.write(message.content)
        except UserWarning:
            self.onMessageReceived_("", message.channelId)

    def disconnect(self):
        self.shouldStop = True
        for t in self.channelThreads.values():
            t.join()

    def _startChannelLoop(self, channelId, channel):
        def channelLoop():
            while not self.shouldStop:
                try:
                    msg = channel.getTimeout(.1)
                except UserWarning:
                    #we've been disconnected. propagate the disconnect and exit
                    self.onMessageReceived_("", channelId)
                    return
                except:
                    self.onMessageReceived_("", channelId)
                    raise

                if msg is not None:
                    self.onMessageReceived_(msg, channelId)
            channel.disconnect()

        self.channelThreads[channelId] = ManagedThread.ManagedThread(target=channelLoop)
        self.channelThreads[channelId].start()

    def _createClient(self, message):
        if message.channelGroup == "SharedState":
            channel = self.sharedStateChannelFactory.createChannel()
        elif message.hostId != '':
            endpoint = message.hostId.split(':')
            channel = self.cumulusChannelFactory.createChannel(endpoint)
        else:
            assert False, "no destination for %s" % message

        client = Client(self.callbackScheduler, channel)
        client.outgoingSequenceNumber = 0
        client.channelGroup = message.channelGroup
        client.hostId = message.hostId
        self._startChannelLoop(message.channelId, client)
        return client

    def _clientForMessage(self, message):
        if not message.channelId in self.clients:
            client = self._createClient(message)
            self.clients[message.channelId] = client
        return self.clients[message.channelId]

    def connect(self, credentials):
        return FakeDeferred({
            'login': credentials[0],
            'sharedStateId': credentials[0],
            'displayName': credentials[0],
            'sharedStateToken': ViewFactory.TEST_KEY_ALL_KEYSPACE_ACCESS_AUTH_TOKEN})




