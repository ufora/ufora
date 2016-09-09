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
import unittest
import shutil
import os
import ufora.native.Storage as StorageNative
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.native.Json as NativeJson






class LogFileDirectory(unittest.TestCase):
    def createLogFileDir(self):
        self.tempdir = tempfile.mkdtemp()
        self.keyspace = SharedState.Keyspace("TakeHighestIdKeyType", NativeJson.Json("test-space"), 1)
        self.keyrange = SharedState.KeyRange(self.keyspace, 0, None, None, True, False)
        self.logFileDir = StorageNative.LogFileDirectory(self.tempdir, self.keyspace, self.keyrange)
        self.baseDir = os.path.split(self.logFileDir.getCurrentLogPath())[0]

    def tearDown(self):
        shutil.rmtree(self.tempdir, True)

    def pathFor(self, type, iter):
        return os.path.join(self.baseDir, '%s-%08x' % (type, iter))

    def touchFile(self, path):
        with open(path, 'w'):
            pass

    def perform_startup(self, logFiles, stateFiles, targetLog, targetState):
        self.createLogFileDir()

        for it in logFiles:
            self.touchFile(self.pathFor('LOG',it))

        for it in stateFiles:
            self.touchFile(self.pathFor('STATE',it))

        self.logFileDir = StorageNative.LogFileDirectory(self.tempdir, self.keyspace, self.keyrange)
        self.assertEqual(self.logFileDir.getCurrentLogPath(), self.pathFor('LOG', targetLog))
        self.assertEqual(self.logFileDir.getNextStatePath(), self.pathFor('STATE', targetState))
        shutil.rmtree(self.tempdir, True)

    def test_basic(self):
        self.createLogFileDir()
        targetSet = set({ix : self.pathFor('LOG', ix) for ix in range(10)}.items())
        for ix in range(10):
            self.touchFile(self.logFileDir.getCurrentLogPath())
            self.touchFile(self.logFileDir.getNextStatePath())
            self.logFileDir.startNextLogFile()
        self.assertEqual(set(self.logFileDir.getAllLogFiles().items()), targetSet)
        shutil.rmtree(self.tempdir, True)

    def test_startup(self):
        self.perform_startup([0], [500], 501, 501)
        self.perform_startup([500], [0], 501, 501)
        self.perform_startup([500], [], 501, 501)
        self.perform_startup([], [500], 501, 501)
        self.perform_startup([], [500], 501, 501)
        self.perform_startup([], range(500)[::10], 491, 491)

