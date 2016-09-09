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
import numpy
import shutil
import Queue
import tempfile
import gc
import unittest

import ufora.util.ManagedThread as ManagedThread
import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import ufora.native.Storage as StorageNative
import ufora.native.SharedState as SharedStateNative
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.distributed.SharedState.SharedStateService as SharedStateService
import ufora.native.TCMalloc as TCMalloc
import ufora.native.Json as NativeJson
import ufora.config.Setup as Setup

import ufora.native.CallbackScheduler as CallbackScheduler
callbackScheduler = CallbackScheduler.singletonForTesting()

json = NativeJson.Json

def smoothArray(array, wlen=128):
    w = numpy.hamming(wlen)
    array = numpy.r_[array[wlen-1:0:-1], array, array[-1:-wlen:-1]]
    return numpy.convolve(array, w / w.sum(), mode="valid")[:len(array)]

def createViewWithNoChannel():
    '''
    used for producing sane events
    '''
    view = DummyView(None)
    view.clientId = 0
    view.eventId = 0
    return view

def performPing(view, manager):
    manager.check()
    view.handlePing()

def produceNullifyingEvent(view, event):
    return view.createNullUpdate(event.key())

def producePartialEvents(view, keyspaces, keyBase, numWrites, numKeys, valueLen):
    with open('/dev/urandom') as randBytes:
        for ix in xrange(numWrites):
            key = SharedState.Key(keyspaces[ix  % len(keyspaces)],
                    (json('%s-%s' % (keyBase, ix % numKeys)),))
            yield view.createKeyUpdate(key, json(randBytes.read(valueLen)))

def createManagerAndView(cacheDir=None, useMemoChannel=False):
    viewChannel, managerChannel = SharedStateNative.InMemoryChannelWithoutMemo(callbackScheduler)

    storage = None

    if cacheDir:
        storage = SharedStateNative.Storage.FileStorage(
            cacheDir,
            10,
            .1,
            useMemoChannel
            )


    manager = SharedStateNative.KeyspaceManager(
            0,
            1,
            0x7fffffff,
            0x7fffffff,
            '',
            storage)

    manager.add(managerChannel)
    view = DummyView(viewChannel)
    view.initialize()
    return view, manager

def subscribeToKeyspace(view, keyspaceNames, keyspaceType):
    keyspaces = [SharedState.Keyspace(keyspaceType, json(keyspaceName), 1)
            for keyspaceName in keyspaceNames]

    keyranges = [SharedState.KeyRange(keyspace, 0, None, None, True, True)
            for keyspace in keyspaces]

    view.subscribe(keyranges)
    return keyspaces, keyranges





def unbundler(message):
    if message.tag != 'Bundle':
        return [message]
    return message.getBundleElements()

class DummyView(object):
    '''
    Simplified view used to test the manager in isolation
    '''
    def __init__(self, viewChannel):
        self.viewChannel = viewChannel
        self.eventId = 0
        self.flushId = 0
        self.pendingMessages = []
        self.clientId = None
        self.masterId = None
        self.generator = None

    def getMessage(self):
        if len(self.pendingMessages) > 0:
            return self.pendingMessages.pop(0)
        self.pendingMessages += unbundler(self.viewChannel.get())
        return self.pendingMessages.pop(0)

    def initialize(self):
        message = self.getMessage()
        self.viewChannel.write(SharedStateNative.MessageRequestSession())

        message = self.getMessage().asInitialize
        self.clientId = message.clientId
        self.masterId = message.masterId
        self.generator = message.generator

    def unsubscribe(self, keyrange):
        self.viewChannel.write(SharedState.MessageOut.Unsubscribe(keyrange))

    def subscribe(self, keyranges):
        # all subscriptions are blocking!
        for keyrange in keyranges:
            self.viewChannel.write(SharedState.MessageOut.Subscribe(keyrange))
        loaded = []
        tr = []
        while len(loaded) < len(keyranges):
            for message in unbundler(self.viewChannel.get()):
                if message.tag != "KeyRangeLoaded":
                    tr.append(message)
                else:
                    loaded.append(message.asKeyRangeLoaded.range)
        assert tuple(sorted(keyranges)) == tuple(sorted(loaded))
        return tr

    def createNullUpdate(self, key):
        tr = StorageNative.createPartialEvent(key, None, self.eventId, self.clientId)
        self.eventId += 1
        return tr

    def createKeyUpdate(self, key, value):
        tr = StorageNative.createPartialEvent(key, value, self.eventId, self.clientId)
        self.eventId += 1
        return tr

    def pushEvent(self, partialEvent):
        self.viewChannel.write(SharedState.MessageOut.PushEvent(partialEvent))


    def getNextMessageOfType(self, expectedType):
        '''
        throw away all messages until a message of "expectedType" is received
        '''
        throwingAway = {}
        while True:
            message = self.getMessage()
            if message.tag == expectedType:
                return message
            else:
                throwingAway[message.tag] = throwingAway.get(message.tag, 0) + 1


    def handlePing(self):
        pingMessage = self.getNextMessageOfType("MinimumId").asMinimumId
        self.eventId = max(self.eventId, pingMessage.maxId)
        self.viewChannel.write(SharedState.MessageOut.MinimumIdResponse(self.eventId))
        logging.info("View would compact to %s", pingMessage.id)
        self.viewChannel.write(SharedState.MessageOut.FlushRequest(self.flushId))
        message = self.getNextMessageOfType("FlushResponse")
        assert message.asFlushResponse.flushId == self.flushId
        self.flushId += 1



class ChannelTester(object):
    def __init__(self, ChannelType, numKeys, keySize):
        self.view = createViewWithNoChannel()
        self.keyspace = SharedState.Keyspace("TakeHighestIdKeyType", json('test'), 1)
        self.viewChannel, self.managerChannel = ChannelType(callbackScheduler)
        self.eventsRead = 0
        self.numKeys = numKeys
        self.keySize = keySize
        self.iterator = enumerate(producePartialEvents(
            self.view,
            [self.keyspace],
            'test',
            self.numKeys,
            1,
            self.keySize))

    def numIters(self):
        return self.numKeys

    def next(self):
        ix, event = self.iterator.next()
        self.viewChannel.write(SharedState.MessageOut.PushEvent(event))
        while self.eventsRead <= ix:
            self.eventsRead += len(unbundler(self.managerChannel.get()))
        return ix

    def tearDown(self):
        self.viewChannel = None

class SocketChannelTester(ChannelTester):
    def __init__(self, numKeys, keySize):
        self.q = Queue.Queue()
        self.port = Setup.config().testPort
        self.server = SimpleServer.SimpleServer(self.port)
        self.server._onConnect = lambda sock, address : self.q.put(sock)

        self.serverThread = ManagedThread.ManagedThread(target=self.server.start)
        self.serverThread.daemon = True
        self.serverThread.start()
        ChannelTester.__init__(self, self.createSocketChannels, numKeys, keySize)

    def createSocketChannels(self, scheduler):
        clientSock = SimpleServer.SimpleServer.connect('localhost', self.port)
        serverSock = self.q.get()
        return (SharedStateService.createClientSocketMessageChannel(scheduler, clientSock),
                    SharedStateService.createServerSocketChannel(scheduler, serverSock))

    def tearDown(self):
        self.server.stop()
        self.serverThread.join()
        ChannelTester.tearDown(self)





class SharedStateMemoryTest(unittest.TestCase):
    def getMemoryUseArray(self, tester):
        try:
            done = False
            memory = numpy.zeros(tester.numIters() + 2)
            memory[0] = TCMalloc.getBytesUsed()
            while not done:
                try:
                    ix = tester.next()
                    memory[ix + 1] = TCMalloc.getBytesUsed()
                except StopIteration:
                    done = True
            memory[-1] = TCMalloc.getBytesUsed()
            return memory
        finally:
            tester.tearDown()

    def memoryTrend(self, toTest):
        A = numpy.array([numpy.arange(0, len(toTest)), numpy.ones(len(toTest))])
        return numpy.linalg.lstsq(A.T, toTest)[0]

    def assertNonIncreasingMemory(self, tester, thresholdRate = 1):
        memory = self.getMemoryUseArray(tester)
        slope, intercept = self.memoryTrend(memory[1:-1])
        self.assertLess(slope, thresholdRate)

    def test_keyspace_cache(self):
        numKeys = 1024 * 256
        before = TCMalloc.getBytesUsed()
        view = createViewWithNoChannel()
        keyspace = SharedState.Keyspace("ComparisonKeyType", json('test'), 1)
        keyrange = SharedState.KeyRange(keyspace, 0, None, None, True, True)
        cache = SharedStateNative.KeyspaceCache(keyrange, None)
        for event in producePartialEvents(view, [keyspace], 'test', numKeys, 1, 8):
            cache.addEvent(event)
        cache.newMinimumId(numKeys)
        view = None

        gc.collect()
        bytesUsed = TCMalloc.getBytesUsed() - before
        self.assertTrue(bytesUsed < 1024 * 16)

    def test_simple_manager(self):
        view = createViewWithNoChannel()
        before = TCMalloc.getBytesUsed()
        keyspace = SharedState.Keyspace("TakeHighestIdKeyType", json('test'), 1)
        cache = SharedStateNative.KeyspaceManager(0, 1, 0x7fffffff, 0x7fffffff, None)
        for event in producePartialEvents(view, [keyspace], 'test', 1024 * 32, 1, 8):
            cache.addEvent(event)
        view = None

        gc.collect()
        bytesUsed = TCMalloc.getBytesUsed() - before
        self.assertTrue(bytesUsed < 1024 * 128)



    def test_socket_equivalent_to_inmemory(self):
        # use this to prove that it's okay to only test
        # with in-memory sockets
        iters = 1024 * 32
        valueSize = 128


        socketMemoryUse =  self.getMemoryUseArray(SocketChannelTester(iters, valueSize))
        inMemMemoryUse  =  self.getMemoryUseArray(
            ChannelTester(SharedStateNative.InMemoryChannel, iters, valueSize)
            )

        socketTrend = self.memoryTrend(smoothArray(socketMemoryUse))
        inMemoryTrend = self.memoryTrend(smoothArray(inMemMemoryUse))

        # rate of increase in bytes per iteration
        self.assertLess(abs(float(socketTrend[0]) - float(inMemoryTrend[0])), 1.0)
        self.assertLess(abs(float(socketTrend[1]) - float(inMemoryTrend[1])), 1024 * 1024)

    def test_in_memory_channels(self):
        self.assertNonIncreasingMemory(
            ChannelTester(SharedStateNative.InMemoryChannel, 1024 * 128, 128),
            thresholdRate=1
            )

        self.assertNonIncreasingMemory(
            ChannelTester(SharedStateNative.InMemoryChannelWithoutMemo, 1024 * 128, 128),
            thresholdRate=.2
            )

    def test_storage(self):
        class StorageTester(object):
            def __init__(self, numIters, valueSize=128, useMemoChannel=True,
                    numKeyspaces=1000, keyType="ComparisonKeyType"):

                self.cacheDir = tempfile.mkdtemp()
                self.fileStore = SharedStateNative.Storage.FileStorage(
                        self.cacheDir, 100, .1, useMemoChannel)

                self.view = createViewWithNoChannel()
                self.keyspaces = [SharedState.Keyspace(keyType, json('test-%s' % ix), 1)
                                            for ix in range(numKeyspaces)]

                self._numIters = numIters
                self.keyspaceStorage = {}
                self.iterator = enumerate(
                        producePartialEvents(
                            self.view,
                            self.keyspaces,
                            'test',
                            self._numIters,
                            1,
                            valueSize))

            def next(self):
                ix, event = self.iterator.next()
                keyspace = event.keyspace()
                keyspaceName = keyspace.name
                if keyspaceName not in self.keyspaceStorage:
                    self.keyspaceStorage[keyspaceName] = self.fileStore.storageForKeyspace(
                                                                                        keyspace,
                                                                                        0)
                self.keyspaceStorage[keyspaceName].writeLogEntry(event)
                if ix % 1024 == 0:
                    for keyspaceStore in self.keyspaceStorage.values():
                        keyspaceStore.compress()
                return ix

            def numIters(self):
                return self._numIters

            def tearDown(self):
                shutil.rmtree(self.cacheDir, True)
                self.fileStore.shutdown()

        # basically only tests the JsonMemoizedCHannel for now
        # but we need to make it more comprehensive and use the nonmemoized
        self.assertNonIncreasingMemory(
                StorageTester(
                    1024 * 8,
                    useMemoChannel=False,
                    numKeyspaces=1),
                thresholdRate=10)

        self.assertNonIncreasingMemory(
                StorageTester(
                    1024 * 8,
                    useMemoChannel=True,
                    numKeyspaces=1),
                thresholdRate=10)


    def test_null_value_is_deleted(self):
        numEvents = 1024 * 64
        valueSize = 128
        numKeys = numEvents

        view = createViewWithNoChannel()
        keyspace = SharedState.Keyspace("ComparisonKeyType", json('test'), 1)
        keyrange = SharedState.KeyRange(keyspace, 0, None, None, True, True)
        cache = SharedStateNative.KeyspaceCache(keyrange, None)
        gc.collect()
        m0 = TCMalloc.getBytesUsed()
        for event in producePartialEvents(view, [keyspace], 'test', numKeys, numKeys, valueSize):
            cache.addEvent(event)
            cache.addEvent(produceNullifyingEvent(view, event))

        cache.newMinimumId(numKeys * 2)
        gc.collect()
        self.assertLess(TCMalloc.getBytesUsed() - m0, 1024 * 4)

