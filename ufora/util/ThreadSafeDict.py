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

from __future__ import with_statement

import threading
import thread

class ThreadSafeDict:
    def __init__(self, vals = dict()):
        self.vals = dict(vals)
        self.lock = threading.RLock()
    def __str__(self):
        return self.vals.__str__()
    def __getitem__(self, index):
        with self.lock:
            return self.vals[index]
    def __setitem__(self, index, val):
        with self.lock:
            self.vals[index] = val
    def updateItem(self, index, f, noneisdel = True):
        with self.lock:
            self.vals[index] = f(self.vals[index] if self.vals.has_key(index) else None)
            if noneisdel and self.vals[index] is None:
                del self.vals[index]
    def update(self, foreignDict):
        with self.lock:
            self.vals.update(foreignDict)
    def has_key(self, index):
        with self.lock:
            return self.vals.has_key(index)
    def keys(self):
        with self.lock:
            return list(self.vals.keys())
    def __delitem__(self, key):
        with self.lock:
            del self.vals[key]
    def __len__(self):
        with self.lock:
            return len(self.vals)
    def scan(self,f):
        with self.lock:
            for k in self.vals:
                f(k, self.vals[k])
    def dictCopy(self):
        with self.lock:
            return dict(self.vals)

