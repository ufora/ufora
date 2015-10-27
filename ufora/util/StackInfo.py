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

'''Stackinfo provides an interface for providing tracebacks of all executing
threads in the system'''

import sys
import traceback
import threading

def getTraces(limit = None):
    '''return a dict of stack traces keyed by thread id for all threads up
    to a certain number of lines determined by "limit"   '''

    aliveThreadIds = set()
    for thread in threading.enumerate():
        aliveThreadIds.add(thread.ident)

    threadDict = {}

    for id, frame in sys._current_frames().iteritems():
        if id in aliveThreadIds:
            threadDict[id] = traceback.format_stack(frame, limit)

    return threadDict



