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

import tempfile
import uuid
import unittest
import threading
import os
import cPickle as pickle
import logging

import ufora.config.Setup as Setup
import ufora.test.InMemoryCluster as InMemoryCluster
import ufora.cumulus.test.TestBase as TestBase
import ufora.native.Hash as HashNative



class ComputingThreads(object):
    def __init__(self):
        self.computingThreads = 0
        self.computingThreadsEvent = threading.Event()
    def onIncrement(self, priority):
        self.computingThreads += 1
        self.computingThreadsEvent.set()
    def onDecrement(self, priority):
        self.computingThreads -= 1
        self.computingThreadsEvent.set()



class InMemoryCumulusTest(unittest.TestCase, TestBase.CumulusTestCases):
    def dumpSchedulerEventStreams(self):
        eventSets = self.extractSchedulerEventStreamsAndParameters()

        rootDir = Setup.config().rootDataDir

        data = pickle.dumps(eventSets)

        fname = "scheduler_events_" + str(HashNative.Hash.sha1(data))

        targetDir = os.path.join(rootDir, "test_failure_artifacts")

        if not os.path.isdir(targetDir):
            os.makedirs(targetDir)

        with open(os.path.join(targetDir, fname), "w") as f:
            f.write(data)

        logging.warn("Wrote scheduler data associated with test failure to %s/%s", targetDir, fname)

    def extractSchedulerEventStreamsAndParameters(self):
        eventSets = []

        for cumulusService in self.simulator.cumuli:
            events = cumulusService.eventHandler.extractEvents()

            eventSets.append(events)

        return eventSets

    def setUp(self):
        self.simulator = InMemoryCluster.InMemoryCluster()

        self.desirePublisher = self.simulator.client
        self.numWorkers = 1
        self.simulator.desireNumCumuli(self.numWorkers)

        self.temporaryDirectoryName = tempfile.mkdtemp()
        self.temporaryFileName = os.path.join(self.temporaryDirectoryName, "temp.dat")
        self.temporaryFileName2 = os.path.join(self.temporaryDirectoryName, "temp2.dat")

        self.gateway = self.simulator.createCumulusGateway(self.simulator.callbackScheduler)
        self.curPriorityIndex = 0
        self.computingThreads = ComputingThreads()
        self.gateway.onCPUCountIncrement = self.computingThreads.onIncrement
        self.gateway.onCPUCountDecrement = self.computingThreads.onDecrement


    def genNextPriority(self):
        self.curPriorityIndex += 1
        return self.curPriorityIndex, uuid.uuid4().hex

    def tearDown(self):
        self.simulator.stop()
        self.simulator.teardown()
        self.gateway.teardown()

