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

import socket
import struct
import sys
import collections
import time
import zlib

class IncompleteReadException(Exception):
    pass
class IncompleteSendException(Exception):
    pass
class NoMessage(Exception):
    pass
        



class NonBlockSocket(object):
    '''Non-blocking socket wrapper which guarantees only whole messages
    appear on it's non-blocking queues'''
    
    def __init__(self, inSock, nodelay = True, littleEndian = True):
        self.prefix_ = "" if littleEndian else ">"
        self.sock_ = inSock
        self.sock_.setblocking(0)
        if nodelay:
            self.sock_.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 0)				
        self.readTime = .001
        self.gotSize_ = False
        self.msgSize_ = 0
        self.buf_ = ""
        self.gotSize_ = False		

        self.incoming = collections.deque()
        self.outgoing = collections.deque()
    
    # element access functions
    def getMessage(self):
        assert len(self.incoming) > 0
        tr = self.incoming.popleft()
        return tr
    
    def putMessage(self, message):
        self.outgoing.append(struct.pack(self.prefix_ + 'i', len(message)) + message)		

    def putMessageCompressed(self, message, level = None):
        compressed = None
        if level is not None:
            compressed = zlib.compress(message, level)
        else:
            compressed = zlib.compress(message)			
        self.outgoing.append(struct.pack(self.prefix_ + 'ii', len(compressed), len(message)) +  compressed)		
    
    def sendBlocking(self):
        self.sock_.setblocking(1)
        tosend = "".join(self.outgoing)		
        self.sock_.sendall("".join(self.outgoing))
        self.sock_.setblocking(0)
        self.outgoing.clear()
    
    def sendToSocket(self):
        msg = ""
        sent = 0				
        try:
            while len(self.outgoing) > 0:
                msg = self.outgoing.popleft()				
                sent = self.sock_.send(msg)
                if sent < len(msg):
                    raise IncompleteSendException("not all sent")
        except Exception as e:
            if sent < len(msg):
                self.outgoing.appendleft(msg[sent:])

    def readFromSocket(self):
        try:
            while True:
                msg = self.readMessage_()
                if msg is not None: # this should not be necessary
                    self.incoming.append(msg)
        except IncompleteReadException as e:
            pass
    
    def readMessage_(self):
        if not self.gotSize_:
            size = struct.unpack(self.prefix_ + 'i', self.read_(4))[0]
            self.gotSize_ = True
            self.msgSize_ = size
        
        self.gotSize_ = True		
        tr = self.read_(self.msgSize_)
        self.gotSize_ = False
        self.msgSize_ = 0
        return tr
    
        
    def read_(self, size):	
        try:
            while len(self.buf_) < size:
                self.buf_ += self.sock_.recv(size - len(self.buf_))
                if len(self.buf_) == size:
                    tr = self.buf_
                    self.buf_ = ""
                    return tr
                else:
                    raise IncompleteReadException("read was fine, but not long enough readSize is " + str(len(self.buf_)) + " and size to read is " + str(size))
        except socket.error as e:	
            raise IncompleteReadException("socket error -- readSize is " + str(len(self.buf_)) + " and size to read is " + str(size))

