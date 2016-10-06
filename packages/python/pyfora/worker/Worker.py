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
import socket
import traceback
import logging
import struct

import pyfora.worker.Common as Common
import pyfora.worker.Messages as Messages
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.PythonObjectRehydrator as PythonObjectRehydrator
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectRegistry as ObjectRegistry
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyAbortSingletons as PyAbortSingletons


class Worker:
    def __init__(self, socket_path):
        logging.info("Worker started, listening on %s", socket_path)

        self.namedSocketPath = socket_path

        assert not os.path.exists(socket_path)

    def executeLoop(self):
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind(self.namedSocketPath)
            sock.listen(1)

            while True:
                connection, _ = sock.accept()

                first_byte = Common.readAtLeast(connection.fileno(), 1)

                if first_byte == Messages.MSG_SHUTDOWN:
                    sock.close()
                    return 0

                if first_byte == Messages.MSG_OOPP_CALL:
                    self.executeOutOfProcessPythonCall(connection)
                elif first_byte == Messages.MSG_TEST:
                    aString = Common.readString(connection.fileno())
                    Common.writeString(connection.fileno(), aString)

                connection.close()
        except:
            logging.error("Worker on %s failed:\n%s", self.namedSocketPath, traceback.format_exc())
            return 1

        logging.info("Worker %s terminated", self.namedSocketPath)

    def executeOutOfProcessPythonCall(self, socket):
        mappings = PureImplementationMappings.PureImplementationMappings()
        mappings.load_pure_modules()

        rehydrator = PythonObjectRehydrator.PythonObjectRehydrator(mappings, allowUserCodeModuleLevelLookups=False)
        convertedInstance = rehydrator.readFileDescriptorToPythonObject(socket.fileno())

        result = convertedInstance()

        registry = BinaryObjectRegistry.BinaryObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=registry
            )

        objId = walker.walkPyObject(result)

        registry.defineEndOfStream()

        msg = registry.str() + struct.pack("<q", objId)
        Common.writeAllToFd(socket.fileno(), msg)

