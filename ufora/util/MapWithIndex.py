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

class MapWithIndex:
    def __init__(self):
        self.keyVal = {}
        self.valKeys = {}
    def __setitem__(self, key, val):
        if key in self.keyVal:
            self.dropKey(key)
        self.keyVal[key] = val
        if val not in self.valKeys:
            self.valKeys[val] = set([key])
        else:
            self.valKeys[val].add(key)
    def __str__(self):
        return str(self.keyVal)
    def __repr__(self):
        return self.keyVal.__repr__()
    def __getitem__(self, key):
        return self.keyVal[key]
    def __len__(self):
        return len(self.keyVal)
    def __delitem__(self, key):
        self.dropKey(key)
    def __contains__(self, key):
        return key in self.keyVal

    def hasKey(self, key):
        return self.keyVal.has_key(key)
    def hasVal(self, val):
        return self.valKeys.has_key(val)
    def keysFor(self, val):
        if val in self.valKeys:
            return self.valKeys[val]
        return set()

    def keys(self):
        return self.keyVal.keys()
    def vals(self):
        return self.valKeys.keys()
    def dropKey(self, key):
        if key in self.keyVal:
            val = self.keyVal[key]
            curSet = self.valKeys[val]
            curSet.discard(key)
            if not curSet:
                del self.valKeys[val]
            del self.keyVal[key]

    def dropValue(self, value):
        keys = set(self.keysFor(value))
        for k in keys:
            self.dropKey(k)


