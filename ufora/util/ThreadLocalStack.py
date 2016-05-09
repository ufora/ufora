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

import threading
import copy

stackIds = [0]
stackLock = threading.Lock()
def allocateStackId():
    with stackLock:
        stackIds[0] += 1
        return stackIds[0]

class ThreadLocalStack(object):
    """
    Implements a stack data structure held in thread local storage.
    """
    threadLocalStorage = threading.local()

    @staticmethod
    def copyContents():
        return dict((copy.copy(key), copy.copy(value)) for key, value in
                ThreadLocalStack.threadLocalStorage.__dict__.iteritems())

    @staticmethod
    def setContents(contentsDict):
        ThreadLocalStack.threadLocalStorage.__dict__.update(contentsDict)

    def __init__(self):
        self.stackId_ = allocateStackId()

    def push(self, element):
        stack = self.getOrCreateStack()
        stack.append(element)

    def pop(self):
        stack = self.getStackAssertIfEmpty()
        stack.pop()
        remaining = len(stack)
        if (remaining == 0):
            setattr(ThreadLocalStack.threadLocalStorage, str(self.stackId_), None)
        return remaining

    @property
    def top(self):
        stack = self.getStackAssertIfEmpty()
        return stack[-1]

    @property
    def topOrNone(self):
        stack = self.getStack()
        return None if stack is None or len(stack) == 0 \
               else stack[-1]

    def getOrCreateStack(self):
        stack = self.getStack()
        if stack is None:
            stack = []
            setattr(ThreadLocalStack.threadLocalStorage, str(self.stackId_), stack)
        return stack

    def getStack(self):
        return getattr(ThreadLocalStack.threadLocalStorage, str(self.stackId_), None)

    def getStackAssertIfEmpty(self):
        stack = self.getStack()

        assert stack is not None
        assert len(stack) > 0

        return stack


#map from type to the actual type descending from ThreadLocalStackPushable.
threadLocalStackPushableDescendents_ = {}

def threadLocalStackPushClassFor_(t):
    """Given 'T', figure out which class actually descended directly from ThreadLocalStackPushable.

    This allows us to define a base class and some subclasses and have all of the subclasses be
    looked up by the interface"""

    if type not in threadLocalStackPushableDescendents_:
        threadLocalStackPushableDescendents_[t] = computeThreadLocalStackPushClassFor_(t)

    return threadLocalStackPushableDescendents_[t]

def computeThreadLocalStackPushClassFor_(t):
    for b in t.__bases__:
        if b is ThreadLocalStackPushable:
            return t

    for b in t.__bases__:
        candidate = threadLocalStackPushClassFor_(b)
        if candidate is not None:
            return candidate

    return None

class NullContextPusher(object):
    def __init__(self, classToPush):
        self.classToPush_ = classToPush

    def __enter__(self):
        toLookup = threadLocalStackPushClassFor_(self.classToPush_)
        ThreadLocalStackPushable.classToStackMap[toLookup].push(None)

    def __exit__(self, *args):
        toLookup = threadLocalStackPushClassFor_(self.classToPush_)
        ThreadLocalStackPushable.classToStackMap[toLookup].pop()



class ThreadLocalStackPushable(object):
    classToStackMap = {}

    def __init__(self):
        toLookup = threadLocalStackPushClassFor_(type(self))
        if toLookup not in ThreadLocalStackPushable.classToStackMap:
            ThreadLocalStackPushable.classToStackMap[toLookup] = ThreadLocalStack()

    def __enter__(self):
        toLookup = threadLocalStackPushClassFor_(type(self))
        ThreadLocalStackPushable.classToStackMap[toLookup].push(self)

    def __exit__(self, *args):
        toLookup = threadLocalStackPushClassFor_(type(self))
        ThreadLocalStackPushable.classToStackMap[toLookup].pop()

    @classmethod
    def getCurrent(cls):
        toLookup = threadLocalStackPushClassFor_(cls)
        if toLookup not in ThreadLocalStackPushable.classToStackMap:
            return None

        return ThreadLocalStackPushable.classToStackMap[toLookup].topOrNone

    @classmethod
    def getNullContext(cls):
        return NullContextPusher(cls)


