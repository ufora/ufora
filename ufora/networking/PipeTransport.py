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

import subprocess
import os
import time
import threading
import ufora.config.Setup as Setup
import ufora.networking.Transport as Transport
import ufora.util.Deferred as Deferred
import ufora.util.ManagedThread as ManagedThread
import ufora.networking.InMemoryTransport as InMemoryTransport
import logging
import Queue

class PipeTransport(Transport.Transport):
    AuthMessage = 'Authentication: '
    LogMessage = 'LOG:'
    DisconnectMessage = 'DISCONNECT'

    def __init__(self, relayHostname, relayHttpsPort = None, messageDelayInSeconds = None):
        """Initialize a PipeTransport.

        messageDelayInSeconds - if not None, then all messages will be delayed by this many
            seconds before being pumped into the receiving channel. This can simulate
            delays talking over the internet.
        """
        self.onMessageReceived = None
        self.onDisconnected = None
        self.inputLoopThread = None
        self.isShuttingDown = False
        self.proxyProcess = None
        self.isConnected = False
        self.messageDelayInSeconds = messageDelayInSeconds
        self.messagePumpThread = None
        self.messagePumpQueue = Queue.Queue()

        self.relayHostname = relayHostname
        if relayHttpsPort:
            self.relayHttpsPort = relayHttpsPort
        else:
            self.relayHttpsPort = Setup.config().relayHttpsPort

        self.proxyStdIn = None
        self.proxyStdOut = None
        self.proxyStdErr = None
        self.proxyOutputThread = None

        logging.info("PipeTransport created for host %s:%s", self.relayHostname, self.relayHttpsPort)

    def connect(self, credentials):
        assert self.onMessageReceived is not None, \
               "onMessageReceived callback must be set before connecting."

        assert isinstance(credentials, tuple) and len(credentials) == 2 and \
            isinstance(credentials[0], str) and isinstance(credentials[1], str)


        deferred = Deferred.Deferred()
        assert self.inputLoopThread is None or not self.inputLoopThread.is_alive()

        localProxyPath = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    '../web/local_proxy/proxy.coffee'
                    )
                )
        relayEndpoint = self.getRelayEndpoint()

        logging.info("PipeTransport.connect relay endpoint is %s", relayEndpoint)

        #print "Connecting to '%s'" % relayEndpoint
        stdInRead,stdInWrite = os.pipe()
        stdOutRead,stdOutWrite = os.pipe()
        stdErrRead,stdErrWrite = os.pipe()

        self.proxyStdIn = os.fdopen(stdInWrite, 'w', 1)
        self.proxyStdOut = os.fdopen(stdOutRead, 'r', 1)
        self.proxyStdErr = os.fdopen(stdErrRead, 'r', 1)
        self.proxyStdInFileDescriptor = stdInWrite
        self.proxyStdOutFileDescriptor = stdOutRead
        self.proxyStdErrFileDescriptor = stdErrRead

        #start our reading threads BEFORE we open the process
        self.inputLoopThread = ManagedThread.ManagedThread(target=self.inputLoop, args=(deferred,))
        self.inputLoopThread.start()
        self.messagePumpThread = ManagedThread.ManagedThread(target=self.messagePumpLoop, args=())
        self.messagePumpThread.start()

        self.proxyOutputThread = ManagedThread.ManagedThread(target=self.outputLoop)
        self.proxyOutputThread.start()

        logging.info("PipeTransport proxyProcess subprocess.Popen call starting")

        proxyEvent = threading.Event()
        def startProxyProcess():
            self.proxyProcess = subprocess.Popen(
                    ['coffee', localProxyPath, '--user', credentials[0], '--password', credentials[1],
                                               '--server', relayEndpoint],
                    stdin=stdInRead,
                    stdout=stdOutWrite,
                    stderr=stdErrWrite
                    )
            proxyEvent.set()

        startProxyThread = ManagedThread.ManagedThread(target=startProxyProcess)
        startProxyThread.start()

        proxyEvent.wait(20.0)

        assert proxyEvent.isSet(), "Failed to start the proxy process."

        #close our copies of the halves of the pipe used by the proxy
        os.close(stdInRead)
        os.close(stdOutWrite)
        os.close(stdErrWrite)

        logging.info("PipeTransport proxyProcess created")

        self.isConnected = True


        return deferred

    def __str__(self):
        return "PipeTransport(%s)" % self.getRelayEndpoint()

    def getRelayEndpoint(self):
        return "%s:%s" % (self.relayHostname, self.relayHttpsPort)

    def send(self, content):
        assert self.isConnected, "PipeTransport is not connected."

        self.proxyStdIn.write(content + '\n')

    def disconnect(self):
        try:
            if self.proxyProcess:
                #disconnect the proxy
                logging.info("Sending proxy shutdown command.")
                self.send(InMemoryTransport.InMemoryTransport.DisconnectMessage)
                self.proxyStdIn.flush()

                self.proxyProcess.wait()
                logging.info("Proxy has shut down successfully")

            self.isShuttingDown = True

            if self.inputLoopThread is not None and not self.isInInputThread():
                self.inputLoopThread.join()

            if self.messagePumpThread is not None:
                self.messagePumpQueue.put((time.time(), PipeTransport.DisconnectMessage))
                if not self.isInPumpThread():
                    self.messagePumpThread.join()

            if self.proxyOutputThread is not None:
                if not self.isInProxyOutputThread():
                    self.proxyOutputThread.join()

            logging.info("PipeTransport has shut down successfully")

        finally:
            self.isShuttingDown = False

    def isInPumpThread(self):
        return threading.currentThread().ident == self.messagePumpThread.ident

    def isInProxyOutputThread(self):
        return threading.currentThread().ident == self.proxyOutputThread.ident

    def isInInputThread(self):
        return threading.currentThread().ident == self.inputLoopThread.ident

    def inputLoop(self, connectDeferred):
        if not self.waitForConnection(connectDeferred):
            return

        # this call doesn't return until the transport is shut down or gets disconnected
        self.processIncomingMessages()

    def outputLoop(self):
        try:
            totalMessageCount = 0
            while not self.isShuttingDown:
                stdErrMessage = self.proxyStdErr.readline().strip()
                totalMessageCount += 1

                if stdErrMessage != "":
                    logging.info("PipeTransport error message #%s: %s", totalMessageCount, stdErrMessage)
        finally:
            logging.info("PipeTransport closing stdErr to proxy")
            self.proxyStdErr.close()

    def processIncomingMessages(self):
        try:
            while not self.isShuttingDown:
                message = self.proxyStdOut.readline().rstrip()

                if message != "":
                    self.messagePumpQueue.put((time.time(), message))

                if message == PipeTransport.DisconnectMessage:
                    return
        finally:
            logging.info("PipeTransport closing stdOut to proxy (fd = %s)", self.proxyStdOutFileDescriptor)
            self.proxyStdOut.close()

    def messagePumpLoop(self):
        while not self.isShuttingDown:
            timestamp, message = self.messagePumpQueue.get()

            if self.messageDelayInSeconds is not None:
                toSleep = self.messageDelayInSeconds + timestamp - time.time()
                if toSleep > 0.0:
                    time.sleep(toSleep)

            if message == PipeTransport.DisconnectMessage:
                self.onDisconnected()
                return

            try:
                if message != "":
                    self.onMessageReceived(message)
            except TypeError as e:
                logging.error('Error decoding message: %s\nMessage: %s', e, message)
            except ValueError as e:
                logging.error('Error decoding message: %s\nMessage: %s',e, message)



    def waitForConnection(self, connectDeferred):
        stdoutData = self.proxyStdOut.readline().rstrip()
        authSucceeded, authInfo = self.parseAuthMessage(stdoutData)
        if authSucceeded:
            logging.info("PipeTransport successfully logged in")
            connectDeferred.callback(authInfo)
        else:
            logging.info("PipeTransport failed to authenticate. message: %s", stdoutData)
            connectDeferred.errback('Failed to authenticate')
        return authSucceeded

    def parseAuthMessage(self, message):
        if not message.startswith(PipeTransport.AuthMessage):
            return (False, {})
        messageFields = message[len(PipeTransport.AuthMessage):].split(',')
        if messageFields[0] != 'OK':
            return (False, {})
        return (True, {
            'login' : messageFields[1],
            'sharedStateId': messageFields[2],
            'displayName': messageFields[3],
            'sharedStateToken' : messageFields[4]
            })


