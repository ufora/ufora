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

"""Implements a service for Cumulus and a socket protocol to connect to it."""

import struct
import pickle
import logging
import traceback
import socket
import sys
import signal
import errno
import os
import threading
import time

import ufora.distributed.Stoppable as Stoppable
import ufora.util.ManagedThread as ManagedThread
import ufora.core.SubprocessRunner as SubprocessRunner

import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.native.CallbackScheduler as CallbackScheduler


class BackendGatewayService(Stoppable.Stoppable):
    def __init__(self, callbackScheduler, channelListener, sharedStateAddress):
        Stoppable.Stoppable.__init__(self)
        self._lock = threading.Lock()
        self.callbackScheduler = callbackScheduler
        self.sharedStateAddress = sharedStateAddress

        self.channelListener = channelListener
        self.channelListener.registerConnectCallback(self.onSubscribableConnection)

        ModuleImporter.initialize()

        self.socketsToDisconnectOnExit = []
        self.procsToKillOnExit = set()
        self.isTornDown_ = False

        self.cleanupThread = ManagedThread.ManagedThread(target=self.cleanupThread_)

    def cleanupThread_(self):
        while not self.shouldStop():
            try:
                procs = []
                joined = []
                with self._lock:
                    procs = list(self.procsToKillOnExit)

                logging.debug("number of procs is %s", len(procs))
                for proc in procs:
                    logging.debug("seeing if proc is still alive")
                    if proc.wait(timeout=0) is not None:
                        logging.info("proc is dead %s", proc)
                        proc.wait()
                        joined.append(proc)
                    else:
                        logging.debug("proc is still alive")

                with self._lock:
                    self.procsToKillOnExit.difference_update(joined)
            except:
                logging.critical("Error in cleanup thread!")
                traceback.print_exc()

            self.getStopFlag().wait(1)


    def startService(self, _):
        logging.info("Starting BackendGatewayService...")
        self.cleanupThread.start()
        self.channelListener.start()
        self.channelListener.blockUntilReady()

    def stopService(self):
        logging.info("Stopping BackendGatewayService...")
        if self.isTornDown_:
            return

        self.isTornDown_ = True

        try:
            self.stop()

            for sock in self.socketsToDisconnectOnExit:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except:
                    logging.warn("Error trying to disconnect socket: %s", traceback.format_exc())

            for proc in self.procsToKillOnExit:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                    proc.join()
                except os.error as e:
                    if e.errno != errno.ESRCH:
                        raise

            self.socketsToDisconnectOnExit = []
            self.cleanupThread.join()

        except:
            traceback.print_exc()
            raise

    def start(self, stopFlag=None):
        while not self.shouldStop():
            time.sleep(0.1)

    def onSubscribableConnection(self, sock, _):
        logging.info("creating a new process to handle connection")

        handlerPid = None
        with self._lock:
            if self.shouldStop():
                return

            scriptName = os.path.join(os.path.split(__file__)[0],
                                      'handleBackendGatewayConnection.py')

            def onStdOut(line):
                logging.info("%s > %s", handlerPid, line)

            def onStdErr(line):
                logging.error("%s > %s", handlerPid, line)

            connectProc = SubprocessRunner.SubprocessRunner([sys.executable, scriptName],
                                                            onStdOut,
                                                            onStdErr)

            self.socketsToDisconnectOnExit.append(sock)

        connectProc.start()
        handlerPid = connectProc.pid
        with self._lock:
            self.procsToKillOnExit.add(connectProc)

        toWrite = pickle.dumps(
            {
                'socketFd' : sock.fileno(),
                'sharedStateAddress': self.sharedStateAddress
            })

        connectProc.write(struct.pack('I', len(toWrite)))
        connectProc.write(toWrite)
        connectProc.flush()

        def waitForProcToFinish():
            connectProc.wait()
            connectProc.stop()
            sock.close()

        threading.Thread(target=waitForProcToFinish).start()



