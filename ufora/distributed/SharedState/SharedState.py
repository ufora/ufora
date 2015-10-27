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
import time
import threading
import ufora.native.SharedState as SharedStateNative
import ufora.native.Json as NativeJson

MessageOut = getattr(SharedStateNative, 'SharedState::MessageOut')
MessageIn = getattr(SharedStateNative, 'SharedState::MessageIn')
LogEntry = getattr(SharedStateNative, 'SharedState::LogEntry')

InMemoryChannel = SharedStateNative.InMemoryChannel
KeyRange = SharedStateNative.makeKeyRange
KeyRangeSet = SharedStateNative.KeyRangeSet
Key = SharedStateNative.Key
Keyspace = SharedStateNative.Keyspace
getClientInfoKeyspace = SharedStateNative.getClientInfoKeyspace

trxTime = 0

def Listener(view):
    """Create a new PySharedStateListener subscribed to 'view' and return it."""
    listener = SharedStateNative.Listener()
    listener.listenToView(view)
    return listener

class Transaction(object):
    def __init__(self, v):
        assert v.connected, "View Disconnected"
        self.v = v
    def __enter__(self):
        self.v.begin()
        self.t = time.time()
    def __exit__(self, *args):
        global trxTime
        if args[0] is None and self.v.connected:
            self.v.end()
        else:
            self.v.abort()
        trxTime += time.time() - self.t

def iterKeys(view, keyspace):
    assert view.isFrozen
    key = view.nextKey(Key(keyspace,  tuple(NativeJson.lowestValue() for x in range(keyspace.dimension))))
    while key is not None:
        yield key
        key = view.nextKey(key)

def iterItems(view, keyspace):
    for key in iterKeys(view, keyspace):
        yield key, view[key]

def subscribeToClientInfoKeyspace(view):
    introspectionKeyspace = getClientInfoKeyspace()
    keyrange = KeyRange(introspectionKeyspace, 1, None, None, True, False)
    view.subscribe(keyrange)


def connectedClientInfo(view):
    """given a view subscribed to the client info keyspace, computes all the connected
    clients"""

    clientInfoKeyspace = SharedStateNative.getClientInfoKeyspace()
    k = view.nextKey(Key(clientInfoKeyspace, (NativeJson.lowestValue(), NativeJson.lowestValue())))

    maxId = 0
    tr = set()
    while k is not None:
        if k.keyspace != clientInfoKeyspace.name:
            return tr, maxId
        if view[k].value() != NativeJson.Json('disconnected'):
            tr.add(k[1])
        maxId = max(maxId, view[k].id())
        k = view.nextKey(k)
    return tr, maxId

def connectedClientIDs(view):
    tr = connectedClientInfo(view)
    return tr[0]


