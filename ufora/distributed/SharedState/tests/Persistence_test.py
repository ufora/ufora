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

import unittest
import os
import tempfile
import time
import random
import shutil
import ufora.native.Json as NativeJson
import logging
import ufora.native.SharedState as SharedStateNative
import ufora.distributed.SharedState.SharedState as SharedState
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.distributed.SharedState.Storage.LogFilePruner as LogFilePruner


def getFiles(baseDir, keyspaceName):
    prefix = os.path.join(baseDir, 'TakeHighestIdKeyType::%s::%s' % (1, keyspaceName), '<null>-<null>::dim(0)')
    return [os.path.join(prefix, x) for x in os.listdir(prefix)]

def getLogFiles(logBaseDir, keyspaceName):
    return [x for x in  getFiles(logBaseDir, keyspaceName) if os.path.split(x)[1].startswith('LOG-')]

def getCurLogFile(logBaseDir, keyspaceName):
    logFiles = [x for x in  getFiles(logBaseDir, keyspaceName) if os.path.split(x)[1].startswith('LOG-')]

    if logFiles:
        return sorted(logFiles)[-1]

    return None

def getStateFiles(logBaseDir, keyspaceName):
    return [x for x in  getFiles(logBaseDir, keyspaceName) if os.path.split(x)[1].startswith('STATE-')]

def getLogFileLen(logBaseDir, keyspaceName):
    curLogfile = getCurLogFile(logBaseDir, keyspaceName)

    if curLogfile is None:
        return 0

    try:
        return os.stat(curLogfile).st_size
    except OSError:
        return 0

class PersistenceTest(unittest.TestCase):
    '''
    A high-level integration test that tests the Persistence infrastrcutre.
    '''

    def randomString(self, size = 64):
        return NativeJson.Json(''.join(chr(random.randint(ord('A'), ord('z'))) for x in range(size)))

    def newHarness(self, cachePath = None, maxLogFileSizeMb=.01):
        if cachePath is None:
            cachePath = self.tempDir
        return SharedStateTestHarness.SharedStateTestHarness(
            True,
            cachePathOverride=cachePath,
            maxLogFileSizeMb=maxLogFileSizeMb,
            pingInterval = 9999999
            )

    def setUp(self):
        self.tempDir = tempfile.mkdtemp()
        self.tempDir2 = tempfile.mkdtemp()

        self.keyspaceName = NativeJson.Json('test-keyspace')
        self.harness = self.newHarness(self.tempDir)
        self.view = self.harness.newView()
        self.harness.subscribeToKeyspace(self.view, self.keyspaceName)

    def tearDown(self):
        if hasattr(self, 'harness') and self.harness is not None:
            self.harness.teardown()
        try:
            shutil.rmtree(self.tempDir)
        except:
            pass
        try:
            shutil.rmtree(self.tempDir2)
        except:
            pass

    def disabled_read_write_kv_maps_using_storage(self):
        for ix in range(1000):
            self.harness.writeToKeyspace(
                self.view,
                self.keyspaceName,
                NativeJson.Json('key%s' % ix),
                NativeJson.Json('test%s' % ix)
                )

        logging.warn("tempDir: %s, tempDir2: %s", self.tempDir, self.tempDir2)

        allItemsFromViewInitial = self.harness.getAllItemsFromView(self.view, self.keyspaceName)
        keyspaceList = [x for x in self.harness.manager.getAllKeyspaces()
                if x != SharedState.getClientInfoKeyspace()]

        self.assertTrue(len(allItemsFromViewInitial) == 1000)
        self.view.flush()
        self.harness.sendPingAndCompact()
        self.harness.teardown()

        try:
            storageA = SharedStateNative.Storage.FileStorage(self.tempDir, 100, 10)
            storageB = SharedStateNative.Storage.FileStorage(self.tempDir2, 100, 10)

            self.assertTrue(len(keyspaceList) == 1)


            for keyspace in keyspaceList:
                storageForKeyspaceA = storageA.storageForKeyspace(keyspace, 0)
                storageForKeyspaceB = storageB.storageForKeyspace(keyspace, 0)

                data = storageForKeyspaceA.readKeyValueMap()
                self.assertTrue(len(data) > 0)

                storageForKeyspaceB.writeKeyValueMap(data)

            self.harness = self.newHarness(self.tempDir2)
            self.view = self.harness.newView()
            self.harness.subscribeToKeyspace(self.view, self.keyspaceName)
            allItemsFromViewFinal = self.harness.getAllItemsFromView(self.view, self.keyspaceName)

            self.assertEqual(allItemsFromViewInitial, allItemsFromViewFinal)
        finally:
            if storageA:
                storageA.shutdown()
            if storageB:
                storageB.shutdown()


    def test_corrupt_logfile(self):
        self.harness.sendPingAndCompact()
        # ensure we have a logfile started here...
        while getLogFileLen(self.tempDir, self.keyspaceName) < 1000:
            self.harness.writeToKeyspace(
                self.view,
                self.keyspaceName,
                NativeJson.Json('key0'),
                NativeJson.Json('test0')
                )

        self.harness.sendPingAndCompact()
        self.harness.teardown()


        self.fileToCorrupt = getCurLogFile(self.tempDir, self.keyspaceName)

        with open(self.fileToCorrupt, 'a') as f:
            size = os.stat(self.fileToCorrupt).st_size
            f.truncate(int(size * .9))


        self.harness = self.newHarness()
        view = self.harness.newView()

        self.harness.subscribeToKeyspace(view, self.keyspaceName)
        while getLogFileLen(self.tempDir, self.keyspaceName) < 10000:
            self.harness.writeToKeyspace(view, self.keyspaceName, NativeJson.Json('key0'), NativeJson.Json('test0'))
        # this segfaults in the failing case, so there's nothing to assert
        self.harness.sendPingAndCompact()




    def writeDataUntilNStatefilesExist(self, number, keyFun, valueFun):
        items = {}
        lastPing = None
        lastCount = 0
        valuesWritten = 0

        try:
            while lastCount < number:
                valuesWritten = valuesWritten + 1
                lastCount = len(getStateFiles(self.tempDir, self.keyspaceName))

                key = keyFun()
                value = valueFun()
                self.harness.writeToKeyspace(self.view, self.keyspaceName, key, value)
                items[key] = value
                if lastPing is None or time.time() - lastPing > .5:
                    self.harness.sendPingAndCompact()
                    lastPing = time.time()

                lastCount = len(getStateFiles(self.tempDir, self.keyspaceName))
            return items
        except:
            logging.error("Total number of statefiles = %s. Values written = %s", lastCount, valuesWritten)
            raise


    def test_corrupt_statefile(self):
        self.writeDataUntilNStatefilesExist(2, lambda : NativeJson.Json('key0'), lambda : NativeJson.Json('test0'))

        fileToCorrupt = sorted(getStateFiles(self.tempDir, self.keyspaceName))[0]

        with open(fileToCorrupt, 'a') as f:
            size = os.stat(fileToCorrupt).st_size
            f.truncate(int(size * .9))
        self.harness.teardown()
        self.harness = self.newHarness()
        view = self.harness.newView()
        self.harness.subscribeToKeyspace(view, self.keyspaceName)

        while getLogFileLen(self.tempDir, self.keyspaceName) < 10000:
            self.harness.writeToKeyspace(view, self.keyspaceName, NativeJson.Json('key0'), NativeJson.Json('test0'))
        ## this segfaults in the failing case, so there's nothing to assert
        self.harness.sendPingAndCompact()



    def test_compact_and_prune(self):
        '''
        Replicates an instance where a statefile and another logfile with a lower iteration number
        can interact given a certain prune / compact cycle
        '''
        def createNewHarnessAndView():
            self.harness = self.newHarness(maxLogFileSizeMb=.08)
            self.view = self.harness.newView()
            self.harness.subscribeToKeyspace(self.view, self.keyspaceName)
            return self.harness, self.view

        self.harness.teardown()
        self.harness, self.view = createNewHarnessAndView()

        totalSize = 0
        self.harness.sendPingAndCompact()
        # ensure we have a logfile started here...
        while getLogFileLen(self.tempDir, self.keyspaceName) < 1024 * 100:
            for ix in range(200):
                self.harness.writeToKeyspace(self.view, self.keyspaceName, NativeJson.Json(self.randomString()), NativeJson.Json(self.randomString()))


        self.harness.manager.check()
        LogFilePruner.pruneLogFiles(self.tempDir)

        self.harness.teardown()
        self.harness, self.view = createNewHarnessAndView()

        loopAgain = True
        while loopAgain:
            for ix in range(200):
                self.harness.writeToKeyspace(self.view, self.keyspaceName, NativeJson.Json(self.randomString()), NativeJson.Json(self.randomString()))
            loopAgain = getLogFileLen(self.tempDir, self.keyspaceName) < 1024 * 100
        self.harness.manager.check()

    def disabled_logfile_prune(self):
        items = self.writeDataUntilNStatefilesExist(10, self.randomString, self.randomString)
        allStateFiles = sorted(getStateFiles(self.tempDir, self.keyspaceName))
        filesToCorrupt = allStateFiles[-5:]
        for fileToCorrupt in filesToCorrupt:
            with open(fileToCorrupt, 'a') as f:
                size = os.stat(fileToCorrupt).st_size
                startByte = int(0)
                bytesToCorrupt = min(1024 * 1024, size - startByte)
                f.seek(startByte)
                f.write(self.randomString(bytesToCorrupt).toSimple())

        self.harness.teardown()

        numStateFilesBeforePrune = len(getStateFiles(self.tempDir, self.keyspaceName))

        LogFilePruner.pruneLogFiles(self.tempDir)

        self.assertLess(len(getStateFiles(self.tempDir, self.keyspaceName)),
                        numStateFilesBeforePrune)


        self.harness = self.newHarness()
        view = self.harness.newView()
        self.harness.subscribeToKeyspace(view, self.keyspaceName)
        allItemsFromView = self.harness.getAllItemsFromView(view, self.keyspaceName)


        view = self.harness.newView()
        self.harness.subscribeToKeyspace(view, self.keyspaceName)
        allItemsFromView = self.harness.getAllItemsFromView(view, self.keyspaceName)
        allKeysInView = set(x[0][0] for x in allItemsFromView)

        self.assertEqual(len(set(items.keys())), len(allKeysInView))
        self.assertEqual(set(items.keys()), allKeysInView)
        self.assertEqual(set(items.items()), set((x[0][0], x[1]) for x in allItemsFromView))

    def test_long_keyspace(self):
        longKeyspace = ''.join(chr(x + ord('a')) for x in range(26)) * 9
        self.harness.subscribeToKeyspace(self.view, NativeJson.Json(longKeyspace))
        self.harness.writeToKeyspace(self.view,
                                     NativeJson.Json(longKeyspace),
                                     NativeJson.Json('key0'),
                                     NativeJson.Json('test0'))

    def disable_disk_space_error(self):
        # root priveledges are required to execute this test
        if os.geteuid() == 0:
            ramdiskPath = tempfile.mkdtemp()
            os.system('mount -t tmpfs -o size=1M tmpfs %s' % ramdiskPath)
            keyspace = NativeJson.Json('test-keyspace-name')
            try:
                self.harness = self.newHarness(cachePath=ramdiskPath)
                self.view = self.harness.newView()
                self.harness.subscribeToKeyspace(self.view, NativeJson.Json(keyspace))
                with open('/dev/urandom') as randBytes:
                    for ix in range(1024):
                        self.harness.writeToKeyspace(
                                self.view,
                                keyspace,
                                NativeJson.Json('key%s' % ix),
                                NativeJson.Json(randBytes.read(1024))
                                )
            except UserWarning:
                # The view will be disconnected and throw this
                pass

            finally:
                try:
                    assert False
                except:
                    pass
                self.harness.manager.shutdown()
                self.harness = None
                self.assertEqual(os.system('umount -f %s' % ramdiskPath), 0)
        else:
            logging.warning("Test can only be run as superuser")

