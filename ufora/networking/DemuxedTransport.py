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
from ufora.networking.ChannelDemuxer import Message, ChannelDemuxer
import logging


class DemuxedTransport(object):
    def __init__(self):
        self.clients = {}
    def onMessageReceived_(self, content, channelId):
        try:
            channel = self.clients[channelId]
            message = Message(
                            channel.channelGroup,
                            channelId,
                            channel.hostId,
                            channel.outgoingSequenceNumber,
                            content
                            )
            channel.outgoingSequenceNumber += 1
            self.onMessageReceived(ChannelDemuxer.encodeMessage(message))
        except Exception:
            import traceback
            logging.error('ERROR: failed to dispatch received message\n%s' % traceback.format_exc())

