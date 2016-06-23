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
import threading
import ufora.networking.ChannelListener as ChannelListener
import ufora.util.ManagedThread as ManagedThread

class MultiChannelListener(object):

    class ListenerRecord(object):
        def __init__(self, index, listener, onPortChanged):
            self.index = index
            self.listener = listener
            self.port = listener.port
            self.listener.onPortBound = self.onPortBound
            self.portBoundEvent = threading.Event()
            self.onPortChanged = onPortChanged
            self.connectionCallback = None

        def start(self):
            self.listener.start()

        def stop(self):
            self.listener.stop()

        def onPortBound(self, originalPort, actualPort):
            if originalPort != actualPort:
                self.port = actualPort
                self.onPortChanged(self.index, actualPort)
            self.portBoundEvent.set()


    def __init__(self, callbackScheduler, ports, channelListenerFactory=ChannelListener.ChannelListener):
        """Constructs a MultiChannelListener that listens on the specified ports

        ports: an iterable of ints representing the port numbers to listen on
        """
        assert(len(ports) > 0)
        self.callbackScheduler = callbackScheduler
        self.lock_ = threading.Lock()
        self.ACCEPT_TIMEOUT_IN_SECONDS = 10.0
        self.GROUP_COMPLETION_TIMEOUT_IN_SECONDS = 20.0

        self.ports = ports
        self.listeners = [MultiChannelListener.ListenerRecord(
                                                    ix,
                                                    channelListenerFactory(
                                                        self.callbackScheduler,
                                                        port,
                                                        portScanIncrement=len(ports)
                                                        ),
                                                    self.onPortChanged
                                                    )
                          for ix, port in enumerate(ports)
                         ]
        self.pendingChannelGroups = {}      # channelGroupId -> (creation_time + GROUP_COMPLETION_TIMEOUT_IN_SECONDS, (port -> channel))
                                            # maps IDs returned by user-provided callbacks to
                                            # dicts from port to channel.
                                            # When a channel is available for all ports,
                                            # self.completionCallback is fired.

        self.acceptedChannels = {}          # channel -> (port, accept_time + ACCEPT_TIMEOUT_IN_SECONDS)
                                            # keeps track of channels that were accepted but
                                            # for which a group ID has not been set yet
        self.completionCallback = None

    def __str__(self):
        # we display the ports in sorted order to get a deterministic
        # representation.
        return "MultiChannelListener(%s)" % ', '.join([str(port) for port in self.ports])

    def start(self, wait=False):
        assert(self.completionCallback is not None)

        for listenerRecord in self.listeners:
            assert listenerRecord.connectionCallback is not None, \
                   'connectionCallback not set for port %d' % listenerRecord.port
            listenerRecord.start()
        if wait:
            for listenerRecord in self.listeners:
                listenerRecord.portBoundEvent.wait()

    def stop(self):
        for listenerRecord in self.listeners:
            listenerRecord.stop()

    def blockUntilReady(self):
        for listenerRecord in self.listeners:
            listenerRecord.listener.blockUntilReady()

    def onPortChanged(self, index, actualPort):
        logging.info("Listening port changed from %d to %d", self.ports[index], actualPort)
        self.ports[index] = actualPort

    def setGroupIdForAcceptedChannel(self, channel, groupId):
        callbackArgsToFire = None

        with self.lock_:
            portIndex = self.acceptedChannels[channel][0]
            assert 0 <= portIndex < len(self.ports)
            del self.acceptedChannels[channel]

            if groupId not in self.pendingChannelGroups:
                self.pendingChannelGroups[groupId] = \
                    (time.time() + self.GROUP_COMPLETION_TIMEOUT_IN_SECONDS, {})

            assert portIndex not in self.pendingChannelGroups[groupId][1]
            self.pendingChannelGroups[groupId][1][portIndex] = channel
            if len(self.pendingChannelGroups[groupId][1]) == len(self.ports):
                # All channels in the group have connected. Firing self.completionCallback
                # making sure that channels are listed in the same order as
                # self.ports
                callbackArgsToFire = [self.pendingChannelGroups[groupId][1][ix] for ix in range(len(self.ports))]
                del self.pendingChannelGroups[groupId]

        if callbackArgsToFire is not None:
            #don't fire under a lock
            logging.debug("Firing callback for %s", groupId)
            self.completionCallback(callbackArgsToFire, groupId)

    def rejectIncomingChannel(self, channel):
        if channel in self.acceptedChannels:
            del self.acceptedChannels[channel]
            channel.disconnect()

    def registerConnectCallbackForPort(self, portIndex, callback):
        assert callback is not None
        oldCallback = self.listeners[portIndex].connectionCallback
        self.listeners[portIndex].connectionCallback = callback

        def connectCallback(channel):
            logging.debug("MultiChannelListener accepted a channel on port %d",
                          self.listeners[portIndex].port)
            self.acceptedChannels[channel] = (portIndex,
                                              time.time() + self.ACCEPT_TIMEOUT_IN_SECONDS)
            callback(portIndex, channel)

            # For simplicity, we don't create a dedicated gc thread or schedule a cleanup
            # callback. Instead we cleanup orphaned channels when new
            # connections are created.
            self.cleanupOrphanedChannels()

        self.listeners[portIndex].listener.registerConnectCallback(connectCallback)
        return oldCallback

    def registerConnectCallbackForAllPorts(self, callback):
        assert callback is not None
        for portIndex in range(len(self.ports)):
            self.registerConnectCallbackForPort(portIndex, callback)

    def registerConnectionCompleteCallback(self, callback):
        assert callback is not None
        oldCallback = self.completionCallback
        self.completionCallback = callback
        return oldCallback

    def cleanupOrphanedChannels(self):
        now = time.time()
        for channel, portIndexAndExpirationTime in self.acceptedChannels.items():
            expiration = portIndexAndExpirationTime[1]
            if expiration < now:
                logging.info("MultiChannelListener closing accepted channel because no " \
                             "groupId has been assigned to it in time.")
                del self.acceptedChannels[channel]
                channel.disconnect()

        for groupId, expirationAndChannels in self.pendingChannelGroups.items():
            expiration = expirationAndChannels[0]
            if expiration < now:
                logging.info("MultiChannelListener closing channels in pending channel group " \
                             "because not all channels in the group have connected within the " \
                             "set timeout.")
                del self.pendingChannelGroups[groupId]
                for channel in expirationAndChannels[1].itervalues():
                    channel.disconnect()


