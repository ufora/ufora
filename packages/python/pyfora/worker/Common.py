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
import struct

def readString(fd):
    string_length = struct.unpack("<L", readAtLeast(fd, 4))[0]
    return readAtLeast(fd, string_length)

def writeString(fd, s):
    writeAllToFd(fd, struct.pack("<L", len(s)))
    writeAllToFd(fd, s)


def readAtLeast(fd, bytecount):
    """Read 'bytecount' bytes from file descriptor fd. raise if we can't."""
    inputData = os.read(fd, bytecount)
    while len(inputData) < bytecount:
        newData = os.read(fd, bytecount - len(inputData))
        assert len(newData) != 0
        inputData += newData
    return inputData

def writeAllToFd(fd, toWrite):
    while toWrite:
        written = os.write(fd, toWrite)
        assert written != 0
        
        if written == len(toWrite):
            return

        toWrite = toWrite[written:]
    
