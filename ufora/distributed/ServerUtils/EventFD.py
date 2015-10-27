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

import fcntl
import os
import struct   
import threading
import errno
import ctypes

# from /usr/include/event.h
EFD_SEMAPHORE = 1
EFD_CLOEXEC = 02000000
EFD_NONBLOCK = 04000
# for initvalue
EFD_MAX = 0xFFFFFFFFFFFFFFFE # this value will cause a write to block...

# an alternative implementation would use fdevent
class SelectEvent(object):
    def __init__(self):
        self._eventfd = EventFD(initval=EFD_MAX, flags=EFD_NONBLOCK)
    def set(self):
        self._eventfd.release(1)
    def clear(self):
        while True:
            try:
                self._eventfd.acquire()
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    return
                raise e
    def fileno(self):
        return self._eventfd.fileno()


_eventfdfun = ctypes.cdll.LoadLibrary("libc.so.6").eventfd 


# portabilaty note: This can be emulated by using a pipe and reading and
# writing to it...
class EventFD(object):
    def __init__(self, initval=0, flags=0):
        self._eventfd = _eventfdfun(initval, flags)
    def read(self):
        return struct.unpack('Q', os.read(self._eventfd, 8))[0]
    def write(self, value):
        return os.write(self._eventfd, struct.pack('Q',value)) 
    def fileno(self):
        return self._eventfd

