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

from ufora.util.DefaultDict import DefaultDict

class TwoWaySetMap:
    """a multimap - tracks a map from keys to multiple values and
    allows users to query the reverse map"""
    
    def __init__(self):
        self.keyVal = DefaultDict(lambda key: set())
        self.valKeys = DefaultDict(lambda key: set())
    def __setitem__(self, key, vals):
        vals = set(vals)
        added = vals - self.keyVal[key]
        removed = self.keyVal[key] - vals
        for v in added:
            self.valKeys[v].add(key)
        for v in removed:
            self.valKeys[v].remove(key)
            if not self.valKeys[v]:
                del self.valKeys[v]
        self.keyVal[key] = vals
        if not self.keyVal[key]:
            del self.keyVal[key]
        
    def add(self, key, value):
        self.keyVal[key].add(value)
        self.valKeys[value].add(key)
    def drop(self, key, value):
        self.keyVal[key].discard(value)
        if not self.keyVal[key]:
            del self.keyVal[key]
        if value in self.valKeys:
            self.valKeys[value].discard(key)
            if not self.valKeys[value]:
                del self.valKeys[value]
    def __str__(self):
        return str(self.keyVal)
    def __repr__(self):
        return self.keyVal.__repr__()
    def __getitem__(self, key):
        return self.keyVal[key]
    def __len__(self):
        return len(self.keyVal)
    def __delitem__(self, key):
        self[key] = set()
    def dropValue(self, val):
        keys = self.keysFor(val)
        for k in list(keys):
            self.keyVal[k].discard(val)
            if not self.keyVal[k]:
                del self.keyVal[k]
            self.valKeys[val].discard(k)
            if not self.valKeys[val]:
                del self.valKeys[val]
    def dropKey(self, key):
        del self[key]
    
    def hasKey(self, key):
        return self.keyVal.has_key(key)
    def hasVal(self, val):
        return self.valKeys.has_key(val)
    def keysFor(self, val):
        if val in self.valKeys:
            return self.valKeys[val]
        else:
            return set()
    def valuesFor(self, key):
        if key in self.keyVal:
            return self.keyVal[key]
        else:
            return set()
    
    def __contains__(self, k):
        return k in self.keyVal
    def keys(self):
        return self.keyVal.keys()
    def vals(self):
        return self.valKeys.keys()


