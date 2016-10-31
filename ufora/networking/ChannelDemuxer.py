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

import base64
import logging
import json
import uuid
import ufora.util.ManagedThread as ManagedThread
import ufora.native.StringChannel as StringChannelNative
import traceback

SUPRESSION_COUNT = 1

class Message(object):
    def __init__(self, channelGroup, channelId, hostId, sequenceNumber, content):
        assert channelGroup != ''
        self.channelGroup = channelGroup
        self.channelId = channelId
        self.hostId = hostId
        self.sequenceNumber = sequenceNumber
        self.content = content
    def __str__(self):
        return "Message(group=%s, channel=%s, host=%s, seq=%s, size=%s)" % \
                (self.channelGroup,
                 self.channelId,
                 self.hostId,
                 self.sequenceNumber,
                 len(self.content))




class ChannelDemuxer(object):
    messageFrameSeparator_ = '<::>'
    MAX_BACKLOG_SIZE = 1024 * 1024 * 100

    def __init__(self, callbackScheduler, transport):
        self.callbackScheduler = callbackScheduler
        self.transport = transport
        self.transport.onMessageReceived = self.onMessageReceived_
        self.generateId = lambda: uuid.uuid4().hex
        self.channelThreads = []
        self.channels = {}
        self.shuttingDown = False
        self.onChannelBroke = None
        self.totalBytesRead = 0
        self.badChannelMessageCount = {}

    def logBytes(self, byteCount):
        priorBytes = self.totalBytesRead
        self.totalBytesRead += byteCount
        if priorBytes / 1024 / 100 != self.totalBytesRead / 1024 / 100:
            logging.debug("ChannelDemuxer read %s MB cumulatively", self.totalBytesRead / 1024 / 1024.0)


    def add(self, channel, channelGroup='', hostId=''):
        if isinstance(channel, StringChannelNative.StringChannel):
            channel = channel.makeQueuelike(self.callbackScheduler)

        channel.group = channelGroup
        channel.incomingSequenceNumber = 0
        channel.outgoingSequenceNumber = 0
        channel.messageBacklog = {}
        channel.byteSize = 0
        thread = ManagedThread.ManagedThread(
                                target = self.channelThread_,
                                args = (channel, channelGroup, hostId)
                                )
        self.channelThreads.append(thread)
        thread.start()


    def close(self):
        self.shuttingDown = True

        try:
            #channels may be disconnecting in the background, so we need to pop these channels
            #off atomically and deal with them. We don't want the 'close' operation to fail,
            #or else later parts of the shutdown process may not run.
            while True:
                channelId, channel = self.channels.popitem()
                try:
                    channel.disconnect()
                except:
                    logging.warn("Failed to disconnect a channel in ChannelDemuxer. " + 
                            " Perhaps it was already disconnected."
                            )
        except KeyError:
            pass

        for thread in self.channelThreads:
            try:
                thread.join()
            except:
                pass

        self.channelThreads = []
        self.channels = {}
        self.shuttingDown = False


    def onMessageReceived_(self, encodedMessage):
        try:
            message = ChannelDemuxer.decodeMessage(encodedMessage)
        except ValueError as e:
            logging.error('Failed to decode message: %s. Error: %s', encodedMessage, e);
            return

        channel = self.channels.get(message.channelId)
        if channel is not None:
            try:
                channel.messageBacklog[int(message.sequenceNumber)] = message
                channel.byteSize += len(message.content)

                self.logBytes(len(message.content))

                if len(message.content) > 100 * 1024:
                    logging.warn("Warning: ChannelDemuxer got a very large message of size %s kB",
                        len(message.content) / 1024.0
                        )

                assert channel.byteSize < ChannelDemuxer.MAX_BACKLOG_SIZE, (
                    "received a message with %s bytes, pushing the backlog to %s bytes, " +
                        " which is >= the max backlog size of %s") % (
                        len(message.content),
                        channel.byteSize,
                        ChannelDemuxer.MAX_BACKLOG_SIZE
                        )

                if int(message.sequenceNumber) == channel.incomingSequenceNumber:
                    self.drainMessageBacklog(channel)
            except UserWarning:
                if not self.shuttingDown:
                    logging.error('Channel disconnected unexpectedly. ID: %s, group: %s' %\
                                  (message.channelId, channel.group)
                                  )
                    raise
            except Exception:
                logging.error('Unexpected exception writing to channel %s.\n%s' % \
                               (message.channelId, traceback.format_exc())
                               )
        else:
            channelId = message.channelId
            if channelId not in self.badChannelMessageCount:
                self.badChannelMessageCount[channelId] = 0

            self.badChannelMessageCount[channelId] += 1

            if self.badChannelMessageCount[channelId] < SUPRESSION_COUNT:
                suppressing = False
                if self.badChannelMessageCount[channelId] == SUPRESSION_COUNT-1:
                    suppressing = True

                logging.info(
                        'Received message "%s..." for non-existent channel with ID: %s%s' % \
                        (repr(message.content[:50]), message.channelId,
                            (". More than %s messages have been received. Suppressing future warnings" 
                                % SUPRESSION_COUNT)
                            if suppressing else ""
                            )
                        )


    def drainMessageBacklog(self, channel):
        while len(channel.messageBacklog) > 0 and \
              channel.incomingSequenceNumber in channel.messageBacklog:
            message = channel.messageBacklog.pop(channel.incomingSequenceNumber)
            
            deleteChannel = False

            if len(message.content) > 0:
                channel.byteSize -= len(message.content)
                channel.incomingSequenceNumber += 1
                try:
                    channel.write(message.content)
                except:
                    logging.error('Writing to channel %s failed because %s', channel, traceback.format_exc())
                    deleteChannel = True
            else:
                deleteChannel = True

            if deleteChannel:
                if message.channelId in self.channels:
                    # this is a disconnect message indicating that the channel is broken
                    logging.debug('Channel %s is disconnected' % message.channelId)

                    del self.channels[message.channelId]
                    channel.disconnect()

                    if self.onChannelBroke is not None:
                        self.onChannelBroke(channel.group)


    def channelThread_(self, channel, channelGroup, hostId):
        channelId = str(self.generateId())
        self.channels[channelId] = channel
        channelIsOpen = True
        while channelIsOpen:
            try:
                content = channel.get()
            except UserWarning:
                if channelId in self.channels:
                    # This means that the disconnect was initiated on the client side and
                    # and we need to notify the server (relay) that we are disconnecting
                    # by sending a zero-length message.
                    content = ''
                    channelIsOpen = False
                else:
                    return

            message = Message(
                            channelGroup,
                            channelId,
                            hostId,
                            channel.outgoingSequenceNumber,
                            content
                            )
            channel.outgoingSequenceNumber += 1
            self.transport.send(ChannelDemuxer.encodeMessage(message))


    @staticmethod
    def decodeMessage(encodedMessage):
        messageDict = json.loads(encodedMessage)
        messageDict['content'] = base64.b64decode(messageDict['content'])
        return Message(**messageDict)

    @staticmethod
    def encodeMessage(message):
        messageDict = dict(message.__dict__)
        messageDict['content'] = base64.b64encode(message.content)
        return json.dumps(messageDict)

