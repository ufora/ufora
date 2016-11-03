#   Copyright 2016 Ufora Inc.
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

import os
import sys
import socket
import struct
import pyfora.worker.spawner as spawner
import pyfora.worker.Spawner as Spawner
import pyfora.worker.Messages as Messages
import pyfora.worker.Common as Common
import pyfora.worker.SubprocessRunner as SubprocessRunner
import time
import threading
import logging

import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator


class WorkerPool:
    def __init__(self, pathToSocketDir, max_processes = None, outOfProcess=True):
        self.pathToSocketDir = pathToSocketDir
        self.outOfProcess = outOfProcess
        self.childSubprocess = None
        self.childThread = None

        assert not os.path.exists(os.path.join(self.pathToSocketDir, "selector"))

        if self.outOfProcess:
            self.childSubprocess = SubprocessRunner.SubprocessRunner(
                [sys.executable, spawner.__file__, pathToSocketDir, "selector"] + (["--max_processes", str(max_processes)] if max_processes is not None else []),
                lambda x: logging.info("spawner OUT> %s", x),
                lambda x: logging.info("spawner ERR> %s", x),
                )

            self.childSubprocess.start()
        else:
            spawnerObject = Spawner.Spawner(pathToSocketDir, "selector", max_processes, False)

            self.childThread = threading.Thread(target=spawnerObject.listen, args=())
            self.childThread.start()

        self.blockUntilConnected()

    def blockUntilConnected(self):
        t0 = time.time()
        TIMEOUT = 10.0

        while time.time() - t0 < TIMEOUT:
            if os.path.exists(os.path.join(self.pathToSocketDir, "selector")):
                return
            else:
                time.sleep(0.01)

        raise UserWarning("Not able to connect to out-of-process worker pool")

    def connect(self, which_worker = "selector"):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(os.path.join(self.pathToSocketDir, which_worker))
        return sock

    def terminate(self):
        aSocket = self.connect()
        Common.writeAllToFd(aSocket.fileno(), Messages.MSG_SHUTDOWN)
        aSocket.close()

        if self.outOfProcess:
            self.childSubprocess.wait()
        else:
            self.childThread.join()

    def _communicate_with_worker(self, callback):
        aSocket = self.connect()
        Common.writeAllToFd(aSocket.fileno(), Messages.MSG_GET_WORKER)
        worker_path = Common.readString(aSocket.fileno())
        aSocket.close()

        aSocket = self.connect(worker_path)
        callback(aSocket)
        aSocket.close()

        aSocket = self.connect()
        Common.writeAllToFd(aSocket.fileno(), Messages.MSG_RELEASE_WORKER)
        Common.writeString(aSocket.fileno(), worker_path)
        aSocket.close()

    def runTest(self, testMessage):
        result = []
        def callback(aSocket):
            Common.writeAllToFd(aSocket.fileno(), Messages.MSG_TEST)
            Common.writeString(aSocket.fileno(), testMessage)
            result.append(Common.readString(aSocket.fileno()))

        self._communicate_with_worker(callback)

        return result[0]
        
    def execute_code(self, toCall):
        result = []
        def callback(aSocket):
            Common.writeAllToFd(aSocket.fileno(), Messages.MSG_OOPP_CALL)

            mappings = PureImplementationMappings.PureImplementationMappings()
            mappings.load_pure_modules()

            binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

            walker = PyObjectWalker.PyObjectWalker(
                mappings,
                binaryObjectRegistry
                )

            objId = walker.walkPyObject(toCall)

            binaryObjectRegistry.defineEndOfStream()

            Common.writeAllToFd(aSocket.fileno(), binaryObjectRegistry.str())
            Common.writeAllToFd(aSocket.fileno(), struct.pack("<q", objId))

            rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowUserCodeModuleLevelLookups=False)
            result.append(rehydrator.readFileDescriptorToPythonObject(aSocket.fileno()))

        self._communicate_with_worker(callback)

        return result[0]
