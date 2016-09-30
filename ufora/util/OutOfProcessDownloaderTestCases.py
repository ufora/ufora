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
import ufora.util.OutOfProcessDownloader as OutOfProcessDownloader
import ufora.config.Mainline as Mainline
import ufora.distributed.util.common as common
import Queue
import time
import logging
import os


def returnsAString():
    return "asdf"

def assertsFalse():
    assert False

def echoInput(toEcho):
    return toEcho

class DoublesString:
    def __init__(self, x):
        self.x = x

    def __call__(self):
        return self.x + self.x

def killSelf():
    import os
    os._exit(0)

class OutOfProcessDownloaderTestCases:
    def test_basic_in(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess=False)
        pool.teardown()

    def test_basic_out(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess=True)
        pool.teardown()

    def test_subprocess_dies(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess=True)

        queue = Queue.Queue()

        for ix in xrange(20):
            try:
                pool.getDownloader().executeAndCallbackWithString(killSelf, lambda s: s)
            except:
                pass

            pool.getDownloader().executeAndCallbackWithString(returnsAString, queue.put)

        pool.teardown()

        self.assertTrue(queue.qsize(), 20)

    def test_in_process(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess=False)

        queue = Queue.Queue()

        pool.getDownloader().executeAndCallbackWithString(returnsAString, queue.put)
        self.assertEqual(queue.get(), "asdf")

        pool.getDownloader().executeAndCallbackWithString(DoublesString("haro"), queue.put)
        self.assertEqual(queue.get(), "haroharo")

        pool.teardown()

    def test_in_process_looping(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess=False)

        queue = Queue.Queue()

        for ix in xrange(10):
            pool.getDownloader().executeAndCallbackWithString(returnsAString, queue.put)
            self.assertEqual(queue.get(), "asdf")

        pool.teardown()

    def test_execute(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1)

        queue = Queue.Queue()

        pool.getDownloader().executeAndCallbackWithString(returnsAString, queue.put)
        self.assertEqual(queue.get(), "asdf")

        pool.getDownloader().executeAndCallbackWithString(DoublesString("haro"), queue.put)
        self.assertEqual(queue.get(), "haroharo")

        pool.teardown()

    def test_throughput(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1)

        queue = Queue.Queue()

        t0 = time.time()
        ix = 0
        while time.time() - t0 < 2.0:
            pool.getDownloader().executeAndCallbackWithString(DoublesString(str(ix)), queue.put)
            self.assertEqual(queue.get(), str(ix) * 2)
            ix = ix + 1

        logging.info("Executed %s out-of-process callbacks/second", ix / 2.0)

        #on the machine in my office we get 20,000/sec. this is a pretty conservative estimate.
        self.assertTrue(ix > 100)

        pool.teardown()

    def test_exception(self):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1)

        queue = Queue.Queue()

        with self.assertRaises(AssertionError):
            pool.getDownloader().executeAndCallbackWithString(assertsFalse, queue.put)

        pool.teardown()

    def test_callable_with_input(self):
        self.verifyCallableWithInput()

    def test_callable_with_input_in_proc(self):
        self.verifyCallableWithInput(actuallyRunOutOfProcess=False)

    def verifyCallableWithInput(self, actuallyRunOutOfProcess=True):
        pool = OutOfProcessDownloader.OutOfProcessDownloaderPool(1, actuallyRunOutOfProcess)
        try:
            queue = Queue.Queue()

            toEcho = "x" * 100000
            def writeInput(fd):
                os.write(fd, common.prependSize(toEcho))

            pool.getDownloader().executeAndCallbackWithString(echoInput, queue.put, writeInput)
            self.assertEqual(queue.get(), toEcho)
        finally:
            pool.teardown()

