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

import ufora.native.Storage as Storage
import ufora.native.Json as NativeJson
import ufora.distributed.SharedState.SharedState as SharedState




def json(text):
    return NativeJson.Json(text)

class FileKeyspaceCacheTest(unittest.TestCase):
    def setUp(self):
        print
        self.keyspace = SharedState.Keyspace("TakeHighestIdType", json('test_keyspace'), 1)
        self.keyrange = SharedState.KeyRange(self.keyspace, 0, None, None, True, True)

    def getKey(self, name):
        return SharedState.Key(self.keyspace, (json(name),))


    def test_one(self):
        logEntries = {}
        def append(path, contents):
            path = os.path.split(path)[1]
            if path not in logEntries:
                logEntries[path] = []
            logEntries[path].append(contents)

        def written(path, contents):
            print path, contents

        def flush(path):
            pass

        def read(path):
            return True, []

        pyOpenFiles = Storage.PythonOpenFiles(
                append,
                written,
                flush,
                read
                )

        fileStore = Storage.FileKeyspaceStorage(
                'test-cache-dir',
                self.keyspace,
                self.keyrange,
                pyOpenFiles.asInterface(),
                .01)

        entries = [Storage.createLogEntryEvent(self.getKey('key-%x' % ix), json('value-%s' % ix), ix)
                for ix in range(100)]

        for e in entries:
            fileStore.writeLogEntry(e)

        success, readEntries = Storage.deserializeAllLogEntries(logEntries.values()[0])
        self.assertEqual(tuple(readEntries), tuple(entries))

