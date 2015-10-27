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

import Queue

class SimpleStringChannel:
    def __init__(self, queueIn, queueOut):
        self.queueIn = queueIn
        self.queueOut = queueOut

    def write(self, s):
        self.queueOut.put(s)

    def get(self, block = True, timeout = None):
        return self.queueIn.get(block = block, timeout = timeout)

    def disconnect(self):
        assert False, "not implemented"

def getTwoSimpleChannels():
    q1 = Queue.Queue()
    q2 = Queue.Queue()

    return SimpleStringChannel(q1, q2), SimpleStringChannel(q2, q1)

