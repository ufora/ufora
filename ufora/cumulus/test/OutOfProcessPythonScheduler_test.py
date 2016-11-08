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

import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory
import pyfora.Exceptions as Exceptions
import pyfora.helpers as helpers
import time
import logging
import unittest
import numpy
import sys

class TestEventQueue:
    def __init__(self):
        self.events = []
        self.completed = 0

    def runTest(self, index, timeout):
        self.events.append(('start',index, time.time()))
        time.sleep(timeout)
        self.events.append(('end',index, time.time()))

        self.completed += 1
        

        
    def resetQueue(self):
        events = self.events
        self.events = []
        return events

    def max_simultaneous_workers(self):
        count = 0
        maxCount = 0
        for event in self.events:
            if event[0] == 'start':
                count += 1
                maxCount = max(maxCount, count)
            elif event[0] == 'end':
                count -= 1

        return maxCount


def runTest(index, timeout):
    with helpers.python:
        #accessing the current module by looking it up in sys.modules
        #prevents the pyfora process isolation mechanisms from kicking
        #in. This only works because these tests use 'in-process' versions
        #of the worker pool, and this kind of escaping finds a common
        #global object. Clients of the system shouldn't generally
        #expect this to work!
        sys.modules[__name__].testEventQueue.runTest(index, timeout)

testEventQueue = TestEventQueue()

class OutOfProcessPythonSchedulerTests(unittest.TestCase):
    def create_executor(self, **kwds):
        return InMemorySimulationExecutorFactory.create_executor(**kwds)

    def test_python_tasks_running_in_process_communicate_with_singletons(self):
        testEventQueue.resetQueue()

        with self.create_executor(threadsPerWorker=2) as fora:
            with fora.remotely.downloadAll():
                results = [runTest(ix, .5) for ix in xrange(10)]
        
        self.assertEqual(len(testEventQueue.events), 20)
        self.assertEqual(testEventQueue.max_simultaneous_workers(), 2)

    def test_python_tasks_fan_out_single_worker(self):
        testEventQueue.resetQueue()

        with self.create_executor(threadsPerWorker=4, workerCount=1, maxMBPerOutOfProcessPythonTask=1, memoryPerWorkerMB=500) as fora:
            with fora.remotely.downloadAll():
                results = [runTest(ix, .5) for ix in xrange(5)]

        self.assertEqual(testEventQueue.max_simultaneous_workers(), 4)

    def test_python_tasks_throttled_by_memory(self):
        testEventQueue.resetQueue()

        with self.create_executor(threadsPerWorker=4, workerCount=1, maxMBPerOutOfProcessPythonTask=400, memoryPerWorkerMB=500) as fora:
            with fora.remotely.downloadAll():
                results = [runTest(ix, .1) for ix in xrange(5)]

        self.assertEqual(testEventQueue.max_simultaneous_workers(), 1)

    def test_python_tasks_fan_out_multiple_workers(self):
        testEventQueue.resetQueue()

        with self.create_executor(threadsPerWorker=1, workerCount=8, maxMBPerOutOfProcessPythonTask=1, memoryPerWorkerMB=500) as fora:
            with fora.remotely.downloadAll():
                results = [runTest(ix, .10) for ix in xrange(160)]

        self.assertTrue(testEventQueue.max_simultaneous_workers() > 1)

    def test_python_tasks_fan_out_multiple_workers_big_tasks(self):
        testEventQueue.resetQueue()

        with self.create_executor(threadsPerWorker=2, workerCount=8, maxMBPerOutOfProcessPythonTask=400, memoryPerWorkerMB=500) as fora:
            with fora.remotely.downloadAll():
                results = [runTest(ix, 0.1) for ix in xrange(80)]

        self.assertTrue(testEventQueue.max_simultaneous_workers() > 1)
