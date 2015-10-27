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

"""A module holding a Queue of events to trigger before the next frame redraw.

In general, our current implementation of ComputedGraph is single threaded.
So we can't have background threads computing values and pushing them into
Tsunami.  As a temporary fix, background threads can push a quick "update"
function into this queue, which will be run by TsunamiApp at the next available
moment. This update function should push any data that's required into mutable
values so that they are reflected apropriately in the interface.
"""


import Queue
import logging
import threading
import time
import traceback

import ufora.BackendGateway.ComputedGraph as ComputedGraph

#a list of quick updates to mutables that can happen in the background
#
#The main tsunami app will pull each item off of here and call it
#with no arguments after every frame.
queues = {}
nextFrameQueues = {}
queuesLock = threading.Lock()

#tell Tsunami not to reload this module if we hit F5
_no_tsunami_reload = True


def getDeferredUpdateQueue(isNextFrameQueue = False):
    graph = ComputedGraph.ComputedGraph.currentGraph()
    assert graph is not None, "Called without a ComputedGraph on the stack."
    queuesDict = queues if not isNextFrameQueue else nextFrameQueues

    with queuesLock:
        queue = queuesDict.get(graph)
        if queue is None:
            queue = Queue.Queue()
            queuesDict[graph] = queue
    return queue

def makeDeferCallback(func):
    """Given a function 'f', make a new function that defers its call to the Queue. 

    That is, if we call makeDeferCallback(f) with 'args', then f will be called on the 
    queue with args.
    """
    def newCallback(*args):
        def caller():
            func(*args)
        push(caller)
    return newCallback

def push(func):
    getDeferredUpdateQueue().put(func)

def pushForNextFrame(func):
    getDeferredUpdateQueue(isNextFrameQueue = True).put(func)

def moveNextFrameToCurFrame():
    curQueue = getDeferredUpdateQueue()
    nextQueue = getDeferredUpdateQueue(isNextFrameQueue = True)
    while True:
        try:
            curQueue.put(nextQueue.get_nowait())
        except Queue.Empty:
            break

def pullAll(timeout=None):
    """pull all available updates. if time.time() exceeds timeout, exit early."""
    try:
        deferredUpdates = getDeferredUpdateQueue()
        while timeout is None or time.time() < timeout:
            updater = deferredUpdates.get_nowait()
            try:
                updater()
            except:
                logging.error(traceback.format_exc())
    except Queue.Empty:
        pass


def pullOne(timeout=None):
    """pull at least one queue element and execute it. If timeout elapses, returns False"""
    try:
        updater = getDeferredUpdateQueue().get(True, timeout)
        try:
            updater()
        except:
            logging.error(traceback.format_exc())
        return True
    except Queue.Empty:
        return False


def drainWithoutExecuting():
    """pull all available updates but do not execute them"""
    try:
        deferredUpdates = getDeferredUpdateQueue()
        while True:
            deferredUpdates.get_nowait()
    except Queue.Empty:
        pass

