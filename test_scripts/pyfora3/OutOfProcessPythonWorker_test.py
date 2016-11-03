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
import tempfile
import pyfora.worker.WorkerPool as WorkerPool
import ufora.config.Mainline as Mainline
import os
import sys
import time
import threading

class Cases:
    def constructWorkerPool(self, socket_path, **kwds):
        raise NotImplementedError("Subclasses implement")

    def test_workerPool(self):
        socket_path = tempfile.mkdtemp()

        pool = self.constructWorkerPool(socket_path)

        for ix in xrange(100):
            testMessage = "this is a string " + str(ix)
            self.assertEqual(pool.runTest(testMessage), testMessage)

        pool.terminate()

        self.assertTrue(not os.listdir(socket_path))

    def test_workerpoolExecutes(self):
        socket_path = tempfile.mkdtemp()

        pool = self.constructWorkerPool(socket_path)

        def generateLambda(arg):
            def f():
                return "received " + str(arg)
            return f

        for ix in xrange(100):
            self.assertEqual(pool.execute_code(generateLambda(ix)), generateLambda(ix)())

        pool.terminate()

        self.assertTrue(not os.listdir(socket_path), os.listdir(socket_path))

    def test_workerpoolParallel(self):
        socket_path = tempfile.mkdtemp()

        pool = self.constructWorkerPool(socket_path, max_processes=10)

        def doThreads(count):
            def generateLambda(arg):
                def f():
                    time.sleep(.5)
                return f

            threads = []

            t0 = time.time()

            for ix in xrange(100):
                threads.append(threading.Thread(target=pool.execute_code, args=(generateLambda(ix),)))
                threads[-1].start()

            for t in threads:
                t.join()

            return time.time() - t0

        doThreads(10)

        elapsed = doThreads(100)

        pool.terminate()

        self.assertTrue(not os.listdir(socket_path))

        self.assertTrue(elapsed < 15.0 and elapsed > 4.99, elapsed)


#we have to run these tests from a separate process. If we run them in the main harness,
#then sometimes there is a lot of memory pressure and "fork" fails. This is really an artifact
#of our test framework, so running these tests in a clean environment makes more sense.
class OutOfProcessPythonWorkerTest(unittest.TestCase, Cases):
    def constructWorkerPool(self, socket_path, **kwds):
        return WorkerPool.WorkerPool(socket_path, outOfProcess=True, **kwds)

    def test_workerpoolParallelWithFailures(self):
        socket_path = tempfile.mkdtemp()

        pool = self.constructWorkerPool(socket_path, max_processes=10)

        valid = []
        invalid = []

        def generateLambda(arg):
            def f():
                time.sleep(.1)
                if arg % 7 == 0:
                    print "terminating"
                    sys.stdout.flush()

                    os._exit(0)
            return f

        def execute(ix):
            try:
                res = pool.execute_code(generateLambda(ix))
                valid.append(ix)
            except:
                invalid.append(ix)

        threads = []

        t0 = time.time()

        for ix in xrange(100):
            threads.append(threading.Thread(target=execute, args=(ix,)))
            threads[-1].start()

        for t in threads:
            t.join()

        pool.terminate()

        self.assertTrue(not os.listdir(socket_path))

        for i in xrange(100):
            if i % 7 == 0:
                assert i in invalid
            else:
                assert i in valid


#we have to run these tests from a separate process. If we run them in the main harness,
#then sometimes there is a lot of memory pressure and "fork" fails. This is really an artifact
#of our test framework, so running these tests in a clean environment makes more sense.
class InProcessPythonWorkerTest(unittest.TestCase, Cases):
    def constructWorkerPool(self, socket_path, **kwds):
        return WorkerPool.WorkerPool(socket_path, outOfProcess=False, **kwds)

if __name__ == '__main__':
    Mainline.UnitTestMainline([])

