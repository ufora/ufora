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
import os
import threading
import time
import traceback

from ufora.distributed.SharedState.Exceptions import SharedStateException
import ufora.config.Setup as Setup
import ufora.distributed.SharedState.Storage.LogFilePruner as LogFilePruner
import ufora.util.ManagedThread as ManagedThread
import ufora.distributed.Service as CloudService
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.native.SharedState as SharedStateNative
import ufora.native.Json as NativeJson
import ufora.distributed.ServerUtils.SimpleServer as SimpleServer

#note that when we create native Channel objects, we need to keep the python object alive
#indefinitely. Otherwise, if we lose the python socket, it will close the file descriptor.
#we can't use os.dup to duplicate the descriptors because it occasionally produces file descriptors
#that conflict with incoming sockets.
allSockets_ = []

def createClientSocketMessageChannel(callbackScheduler, sock):
    allSockets_.append(sock)
    return SharedStateNative.ClientSocketMessageChannel(callbackScheduler, sock.fileno())

def createServerSocketChannel(callbackScheduler, sock):
    allSockets_.append(sock)
    return SharedStateNative.ServerSocketChannel(callbackScheduler, sock.fileno())


def KeyspaceManager(randomSeed,
                    numManagers,
                    backupInterval=60*10,
                    pingInterval=20,
                    cachePathOverride=None,
                    maxOpenFiles=None,
                    maxLogFileSizeMb=10,
                    hmacKey=None):
    if cachePathOverride is None:
        cachePathOverride = Setup.config().sharedStateCache

    if hmacKey is None:
        hmacKey = Setup.config().tokenSigningKey

    if maxOpenFiles is None:
        import resource
        maxOpenFiles = min(resource.getrlimit(resource.RLIMIT_NOFILE)[0] / 2, 1000)

    if cachePathOverride != "":
        logging.info(
            "Creating FileStorage(cachePathOverride=%s, maxOpenFiles=%s, maxLogFileSizeMb=%s)",
            cachePathOverride,
            maxOpenFiles,
            maxLogFileSizeMb)
        storage = SharedStateNative.Storage.FileStorage(cachePathOverride,
                                                        maxOpenFiles,
                                                        maxLogFileSizeMb)
    else:
        storage = None

    logging.info("Token signing key is %s", hmacKey)
    return SharedStateNative.KeyspaceManager(
        randomSeed,
        numManagers,
        backupInterval,
        pingInterval,
        hmacKey,
        storage
        )


class SharedStateService(CloudService.Service):
    def __init__(self, callbackScheduler, tokenSigningKey=None, cachePathOverride=None, port=None):
        self.callbackScheduler = callbackScheduler
        port = Setup.config().sharedStatePort
        logging.info("Initializing SharedStateService with port = %s", port)

        self.cachePath = cachePathOverride if cachePathOverride is not None else \
                         Setup.config().sharedStateCache

        if self.cachePath != '' and not os.path.exists(self.cachePath):
            os.makedirs(self.cachePath)

        CloudService.Service.__init__(self)
        self.socketServer = SimpleServer.SimpleServer(port)
        self.keyspaceManager = KeyspaceManager(
            0,
            1,
            pingInterval=120,
            cachePathOverride=cachePathOverride,
            hmacKey=tokenSigningKey
            )


        self.socketServer._onConnect = self.onConnect
        self.socketServerThread = ManagedThread.ManagedThread(target=self.socketServer.start)
        self.logfilePruneThread = ManagedThread.ManagedThread(target=self.logFilePruner)

        self.stoppedFlag = threading.Event()

    def logFilePruner(self):
        if self.cachePath == '':
            return

        logging.info("Starting log-file pruning loop")
        while not self.stoppedFlag.is_set():
            try:
                LogFilePruner.pruneLogFiles(self.cachePath)
            except:
                # We don't want to stop pruning just because there was an
                # error
                logging.error("Error pruning log files in %s\n%s",
                              self.cachePath,
                              traceback.format_exc())
            t = time.time()
            while not self.stoppedFlag.is_set() and \
                    time.time() - t < Setup.config().sharedStateLogPruneFrequency:
                time.sleep(1)

    def compressOrphandLogFiles(self):
        for keyspaceDir in os.listdir(self.cachePath):
            keyspaceType, dimensions, keyspaceName = keyspaceDir.split('::')
            dimensions = int(dimensions)

            keyspace = SharedState.Keyspace(keyspaceType,
                                            NativeJson.Json.parse(keyspaceName),
                                            dimensions)
            for i in range(dimensions):
                logging.info("Compressing keyspace: %s", keyspaceName)
                keyspaceStorage = self.keyspaceManager.storage.storageForKeyspace(keyspace, i)
                keyspaceStorage.compress()

    def onConnect(self, sock, address):
        if not self.socketServer._started:
            raise SharedStateException("adding socket to server that isn't started")
        chan = createServerSocketChannel(self.callbackScheduler, sock)
        self.keyspaceManager.add(chan)

    def stopService(self):
        self.stoppedFlag.set()
        self.socketServer.stop()
        self.keyspaceManager.shutdown()
        self.keyspaceManager = None

        logging.debug('stopping shared state socket server')
        self.socketServerThread.join()
        logging.debug('stopped shared state socket server')

        self.logfilePruneThread.join()

    def startService(self):
        if self.cachePath != '':
            # Compress all keyspaces before starting to accept connections.
            # This increases the loading speed of keyspaces
            self.compressOrphandLogFiles()
            LogFilePruner.pruneLogFiles(self.cachePath)

        self.socketServerThread.start()
        self.logfilePruneThread.start()

    def blockUntilListening(self):
        self.socketServer.blockUntilListening()



