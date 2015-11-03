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

import time
import pyfora
import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases


class InMemoryExecutorTestCases(ExecutorTestCases.ExecutorTestCases):
    def test_pyfora_s3_read(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            payload = "this is some data"
            s3().setKeyValue("bucketname", "key", payload)

            remote = executor.importS3Dataset("bucketname", "key").result()
            remoteResult = remote.toLocal().result()
            self.assertEqual(payload, remoteResult)

            assert s3 is not None

    def test_pyfora_s3_write_badKey(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            def f():
                return "this is a string"

            remote = executor.submit(f).result()

            noneOrExceptionFuture = executor.exportS3Dataset(remote, "bucket", 10)
            with self.assertRaises(pyfora.PyforaError):
                noneOrExceptionFuture.result()

    def test_pyfora_s3_write_valueNotString(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            def f():
                return 10

            remote = executor.submit(f).result()

            noneOrExceptionFuture = executor.exportS3Dataset(remote, "bucket", "key")
            with self.assertRaises(pyfora.PyforaError):
                noneOrExceptionFuture.result()

    def test_pyfora_s3_write_succeeds(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            def f():
                return "this is a string"

            remote = executor.submit(f).result()

            noneOrExceptionFuture = executor.exportS3Dataset(remote, "bucket", "key")
            self.assertIs(noneOrExceptionFuture.result(), None)

            self.assertTrue(s3().getKeyValue("bucket", "key") == "this is a string")

    def test_execute_in_loop(self):
        fora = self.create_executor()

        def add(x, y):
            return x+y

        with fora:
            t0 = time.time()
            ct = 0
            while ct < 100:
                fora.submit(add, 1, 2).result().toLocal().result()
                ct += 1
        self.assertTrue(time.time() - t0 < 4.0)

    def test_slicing_operations_1(self):
        a = "testing"
        l = len(a)
        with self.create_executor() as fora:
            pythonResults = []
            futures = []
            for idx1 in range(-l - 1, l + 1):
                for idx2 in range(-l - 1, l + 1):
                    def f():
                        return a[idx1:idx2]
                    futures.append(
                        fora.submit(f)
                        )
                    try:
                        result = f()
                        pythonResults.append(result)
                    except:
                        pass
        foraResults = self.resolvedFutures(futures)
        self.assertTrue(len(foraResults) > (l * 2 + 1) ** 2)
        self.assertEqual(pythonResults, foraResults)


    def test_slicing_operations_2(self):
        a = "abcd"
        l = len(a) + 1
        with self.create_executor() as fora:
            pythonResults = []
            futures = []
            for idx1 in range(-l, l):
                for idx2 in range(-l, l):
                    for idx3 in range(-l, l):
                        def f():
                            return a[idx1:idx2:idx3]
                        futures.append(
                            fora.submit(f)
                            )
                        try:
                            result = f()
                            pythonResults.append(result)
                        except:
                            pass

            foraResults = self.resolvedFutures(futures)
            # we are asserting that we got a lot of results
            # we don't expect to have (l * 2 -1)^3, because we expect some of the
            # operations to fail
            self.assertTrue(len(foraResults) > 500)
            self.assertEqual(pythonResults, foraResults)

    def test_slicing_operations_3(self):
        a = "abcd"
        l = len(a)
        l2 = -l + 1
        def f():
            toReturn = []
            for idx1 in range(l2, l + 1):
                for idx2 in range(l2, l + 1):
                    for idx3 in range(l2, l + 1):
                        if(idx3 != 0):
                            r = a[idx1:idx2:idx3]
                            toReturn = toReturn + [r]
            return toReturn
        self.equivalentEvaluationTestThatHandlesExceptions(f)

    
