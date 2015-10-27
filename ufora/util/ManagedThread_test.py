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
import sys

from ufora.util.ManagedThread import ManagedThread

import ufora.util.ThreadLocalStack as ThreadLocalStack

class TestPushable(ThreadLocalStack.ThreadLocalStackPushable):
    def __init__(self, ix):
        ThreadLocalStack.ThreadLocalStackPushable.__init__(self)
        self.ix = ix


class TestManagedThread(unittest.TestCase):
    def setUp(self):
        self.testValue = 0
        self.exception = None

    def stackCheckTest(self):
        try:
            current = TestPushable.getCurrent()
            self.assertIsNotNone(current)
        except Exception as e:
            self.exception = e

    def incrementTestValue(self):
        self.testValue += 1

    def setTestValue(self, value):
        self.testValue = value

    def allocateTooMuchMemory(self):
        x = "x" * (1024*1024*1024*1024)

    def test_createManagedThread(self):
        def doNothing():
            pass
        thread = ManagedThread(target=doNothing)

    def test_daemonByDefault(self):
        def doNothing():
            pass
        thread = ManagedThread(target=doNothing)

        self.assertTrue(thread.daemon)

    def test_thread_local_storage_dict(self):
        tester = TestPushable(2)
        with tester:
            thread = ManagedThread(target=self.stackCheckTest)
        thread.start()
        thread.join()
        if self.exception is not None:
            raise self.exception


    def test_startManagedThread(self):
        thread = ManagedThread(target=self.incrementTestValue)
        thread.start()
        thread.join()

        self.assertEqual(self.testValue, 1)

    def test_startWithArgument(self):
        thread = ManagedThread(target=self.setTestValue, args=(2,))
        thread.start()
        thread.join()

        self.assertEqual(self.testValue, 2)

    def test_outOfMemory(self):
        def handleException(ex):
            self.assertTrue(isinstance(ex, Exception))
            self.setTestValue(3)


        # temporarily redirect stderr to devnull to supress tcmalloc output
        # without this, tcmalloc prints out an error message when we try to allocate
        # too big a block.
        #
        # we need to use low level file descriptor trickery because
        # the code that writes to stderr is not python code but C code.
        sys.stderr.flush()
        newstderr = os.dup(sys.stderr.fileno())
        devnull = open(os.devnull, 'w')
        os.dup2(devnull.fileno(), sys.stderr.fileno())
        devnull.close()

        thread = ManagedThread(target=self.allocateTooMuchMemory)
        thread.criticalErrorHandler = handleException
        thread.start()
        thread.join()

        # restore stderr to its original state
        os.dup2(newstderr, sys.stderr.fileno())

        self.assertEqual(self.testValue, 3)

