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

import ufora.native.Hash as HashNative
import sys
import hashlib
import cPickle as pickle
import weakref
import sys

def getClosure(func):
    tr = func.__closure__
    if tr is None:
        return ()
    return [x.cell_contents for x in tr]

def funcEx_():
    pass

funcType_ = type(funcEx_)

class WeakObjectAssociationDict:
    def __init__(self):
        self.weakObjectsById = weakref.WeakValueDictionary()
        self.weakValuesById = dict()

    def __setitem__(self, k, v):
        self.weakObjectsById[id(k)] = k
        self.weakValuesById[id(k)] = v

    def __getitem__(self, k):
        if id(k) in self.weakObjectsById:
            return self.weakValuesById[id(k)]

    def __contains__(self, k):
        return id(k) in self.weakObjectsById

memoizedHashes_ = WeakObjectAssociationDict()

badTypes = set()

def stableHashForIterable_(iterable, unhashableObjectPolicy):
    return stableHashOfHashes_([
            stableShaHashForObject(x, unhashableObjectPolicy) for x in iterable
            ]
        )


def stableHashOfHashes_(hashes):
    return str(HashNative.Hash.sha1(":".join(hashes)))

theNoneHash_ = str(HashNative.Hash.sha1("Nothing"))

class AClass:
    pass
class AClass2(object):
    pass

pickleablePrimitiveTypes = set([
    float,
    int,
    long,
    unicode,
    str,
    type,
    type(AClass), #old-style class objects
    type(AClass2), #new-style class objects
    type(HashNative.Hash), #boost python class objects
    bool
    ])

hashFunctionsByType = {}
typesUsedByIDMemo = set()

#hashing policies
def pickleUnhashableObjects(val):
    return str(HashNative.Hash.sha1(pickle.dumps(val,0)))

def useIdForUnhashableObjects(val):
    try:
        if val.__class__ not in typesUsedByIDMemo:
            print "Using ", val, " as a StableHash value, but keying on instance ID"
            typesUsedByIDMemo.add(val.__class__)
    except AttributeError:
        pass
    return str(id(val))

def allObjectsShouldBeHashable(val):
    assert False, "Unable to hash %s of type %s" % (val, type(val))



def stableShaHashForObject(x, unhashableObjectPolicy = allObjectsShouldBeHashable):
    if x in memoizedHashes_:
        return memoizedHashes_[x]
    
    assert type(x) not in badTypes, type(x)
    
    #first, check if its a computed graph location or a function. These have special forms required
    #to make them work
    if type(x) in hashFunctionsByType:
        h = hashFunctionsByType[type(x)](x, unhashableObjectPolicy)
        
        memoizedHashes_[x] = h
        return h
    
    if isinstance(x, funcType_):
        h = stableHashForIterable_( 
            (getClosure(x),
                x.func_code.co_code, 
                x.func_globals['__version__'] if '__version__' in x.func_globals else 0
                ),
            unhashableObjectPolicy
            )
        memoizedHashes_[x] = h
        return h

    #tuples, lists, dicts, and sets, we can't use the memo because of the weakrefs. So,
    #we just hash their hashes. If they have anything big/complex in them, we'll hash those.
    if isinstance(x, tuple) or isinstance(x, list):
        return stableHashOfHashes_(
            [stableShaHashForObject(x, unhashableObjectPolicy) for x in x]
            )
    
    elif isinstance(x, dict):
        return stableHashOfHashes_(
            sorted([stableShaHashForObject(x, unhashableObjectPolicy) for x in x.iteritems()])
            )

    elif isinstance(x, set) or isinstance(x, frozenset):
        return stableHashOfHashes_(
            sorted([stableShaHashForObject(elt, unhashableObjectPolicy) for elt in x])
            )

    elif x is None:
        return theNoneHash_

    if isinstance(x,unicode):
        x = str(x)

    #just a regular object. first, see if it has a getstate function
    objectState = None
    try:
        objectState = (x.__class__.__getstate__(x), x.__class__)
    except AttributeError:
        pass

    if objectState is None:
        try:
            objectState = (x.__class__, x.__class__.__stable_hash_state__(x))
        except AttributeError:
            pass

    if objectState is not None:
        #yes, so we use that
        h = stableHashForIterable_(objectState, unhashableObjectPolicy)
    else:
        #no - check if we should use pickle
        if type(x) in pickleablePrimitiveTypes:
            h = str(HashNative.Hash.sha1(pickle.dumps(x,0)))
        else:
            #we can't use pickle, so the object instance ID is the next best thing
            h = unhashableObjectPolicy(x)

    try:
        memoizedHashes_[x] = h
    except TypeError:
        #some types can't go in the memo
        pass

    return h

