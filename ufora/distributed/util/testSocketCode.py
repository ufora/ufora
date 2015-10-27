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

import ufora.distributed.util.common as common

import unittest
import Queue
import threading
import uuid
import socket
import time
import socket

class DyingSocket(socket.socket):
    '''This socket throws a generic socket error for test cases'''
    def send(*args, **kwargs):
        raise socket.error()
    def recv(*args, **kwargs):
        return socket.socket.recv(*args, **kwargs)


class DelaySocket(socket.socket):
    '''This socket pauses before sending for exposing test cases'''
    def send(*args, **kwargs):
        time.sleep(5)
        socket.socket.send(*args, **kwargs)
    def recv(*args, **kwargs):
        return socket.socket.recv(*args, **kwargs)

def createSocketPairs(num):
    sockIdQueue = Queue.Queue()
    socketOutputQueue = Queue.Queue()

    def socketCreatorThread():
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(('localhost', 56000))
        listener.listen(4)
        while True:
            id = sockIdQueue.get()
            if id is None:
                return 
            sock, addr = listener.accept()
            socketOutputQueue.put((id, sock))
    
    t = threading.Thread(target=socketCreatorThread)
    t.start()

    def genSockPair():
        id = uuid.uuid4().hex[:16]
        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockIdQueue.put(id)
        got = False
        while not got:
            try:
                clientSock.connect(('localhost', 56000))
                got = True
            except socket.error:
                time.sleep(.001)
        sockId, serverSock = socketOutputQueue.get()
        assert sockId == id
        return clientSock, serverSock

    tr = [genSockPair() for x in range(num)]

    sockIdQueue.put(None)
    t.join()
    return tr




class NonblockingTest(unittest.TestCase):
    def test_sockets(self):
        def genData():        
            return ''.join(['a' for x in range(1024)] * 256 )
            

        socks = createSocketPairs(400)
        sender = common.NonBlockingSocketSender()
        receiver = sender
        
        sent = {}
        for send, recv in socks:
            dat = genData()
            sender.writeToSock(send, dat)
            recv = receiver.register(recv)
            sent[(send, recv)] = dat
            
            

        verified = set()
        while sender.sendToAll():
            receiver.readAll()
            for (_, recv), data in sent.iteritems():
                if recv not in verified:
                    try:
                        self.assertTrue(recv.readMessage() == data)
                        verified.add(recv)
                    except common.SocketReaderException:
                        pass
            
            
        
    def test_deadlock(self):
        # a deadlock will occur if the listener holds a lock that is held
        # during a write held by another thread..
        lockA = threading.RLock()
        lockB = threading.RLock()


