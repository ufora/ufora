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

    def test_pyfora_s3_read_bad_key(self):
        with self.create_executor() as executor:
            with self.assertRaises(pyfora.PyforaError):
                executor.importS3Dataset("no_such_bucket", "key").result()


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
            results = []
            def f(idx1, idx2):
                try:
                    return ("OK", a[idx1:idx2])
                except:
                    return "FAIL"

            for idx1 in range(-l - 1, l + 1):
                for idx2 in range(-l - 1, l + 1):
                    results = results + [f(idx1, idx2)]

            return results

        self.equivalentEvaluationTest(f)

    def test_slicing_operations_2(self):
        a = "abcdefg"

        def f():
            l = len(a) + 1

            def trySlice(low,high,step):
                try:
                    return ("OK", a[low:high:step])
                except:
                    return "FAIL"

            result = []
            for idx1 in xrange(-l,l):
                for idx2 in xrange(-l,l):
                    for idx3 in xrange(-l,l):
                        if idx3 != 0:
                            result = result + [trySlice(idx1, idx2, idx3)]
            return result

        self.equivalentEvaluationTest(f)

    def test_xrange(self):
        def f():
            low = 0
            res = []
            for high in [None] + range(-7,7):
                for step in [-3,-2,-1,None,1,2,3]:
                    try:
                        if high is None:
                            res = res + [range(low)]
                        elif step is None:
                            res = res + [range(low, high)]
                        else:
                            res = res + [range(low, high, step)]
                    except Exception:
                        res = res + ["Exception"]

        self.equivalentEvaluationTest(f)

    def test_types_and_combos(self):
        types = [bool, str, int, type, object, list, tuple, dict]
        instances = [10, "10", 10.0, None, True, [], (), {}] + types
        callables = types + [lambda x: x.__class__]

        for c in callables:
            for i in instances:
                self.equivalentEvaluationTestThatHandlesExceptions(
                    c, i, comparisonFunction=lambda x, y: x == y
                    )


    def test_filtered_generator_expression(self):
        for ct in [0,1,2,4,8,16,32,64,100,101,102,103]:
            self.equivalentEvaluationTest(
                lambda: sum(x for x in xrange(ct) if x < ct / 2))
            self.equivalentEvaluationTest(
                lambda: list(x for x in xrange(ct) if x < ct / 2))
            self.equivalentEvaluationTest(
                lambda: [x for x in xrange(ct) if x < ct / 2])

    def test_filtered_nested_expression(self):
        for ct in [0, 1, 2, 4, 8, 16, 32, 64]:
            self.equivalentEvaluationTest(
                lambda: sum((outer * 503 + inner for outer in xrange(ct) \
                             for inner in xrange(outer))))
            self.equivalentEvaluationTest(
                lambda: sum((outer * 503 + inner for outer in xrange(ct) \
                             if outer % 2 == 0 for inner in xrange(outer))))
            self.equivalentEvaluationTest(
                lambda: sum((outer * 503 + inner for outer in xrange(ct) \
                             if outer % 2 == 0 for inner in xrange(outer) \
                             if inner % 2 == 0)))
            self.equivalentEvaluationTest(
                lambda: sum((outer * 503 + inner for outer in xrange(ct) \
                             for inner in xrange(outer) if inner % 2 == 0)))

    def test_list_getitem_exhaustive_1(self):
        sz = 3
        def f():
            x = range(sz)
            def trySlice(start, stop, step):
                try:
                    return ("OK", x[start:stop:step])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            values = range(-sz, sz) + [None, sz - 10, sz + 10]

            res = []
            for start in values:
                for stop in values:
                    for step in values:
                        res = res + [trySlice(start, stop, step)]

        self.equivalentEvaluationTest(f)

    def test_list_getitem_exhaustive_2(self):
        sz = 3
        def f():
            x = range(sz)
            def trySlice(start, stop):
                try:
                    return ("OK", x[start:stop])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            values = range(-sz, sz) + [None, sz - 10, sz + 10]

            res = []
            for start in values:
                for stop in values:
                    res = res + [trySlice(start, stop)]

            return res

        self.equivalentEvaluationTest(f)

    def test_list_getitem_exhaustive_3(self):
        sz = 3
        def f():
            x = range(sz)
            def tryGetItem(ix):
                try:
                    return ("OK", x[ix])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            indices = range(-sz, sz) + [sz - 10, sz + 10, 1.0, None]

            res = []
            for ix in indices:
                res = res + [tryGetItem(ix)]

            return res

        self.equivalentEvaluationTest(f)

    def test_tuple_getitem_exhaustive_1(self):
        sz = 3
        def f():
            x = tuple(range(sz))
            def tryGetItem(ix):
                try:
                    return ("OK", x[ix])
                except Exception as e:
                    return "except"

                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            indices = range(-sz, sz) + [sz - 10, sz + 10, 1.0, None]

            res = []
            for ix in indices:
                res = res + [tryGetItem(ix)]

            return res

        self.equivalentEvaluationTest(f)

    def test_tuple_getitem_exhaustive_2(self):
        sz = 3
        def f():
            x = tuple(range(sz))
            def trySlice(start, stop):
                try:
                    return ("OK", x[start:stop])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            values = range(-sz, sz) + [None, sz - 10, sz + 10]

            res = []
            for start in values:
                for stop in values:
                    res = res + [trySlice(start, stop)]

            return res

        self.equivalentEvaluationTest(f)

    def test_string_getitem_exhaustive_1(self):
        def f():
            x = "asd"
            def trySlice(start, stop, step):
                try:
                    return ("OK", x[start:stop:step])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            sz = len(x)
            values = range(-sz, sz) + [None, sz - 10, sz + 10]

            res = []
            for start in values:
                for stop in values:
                    for step in values:
                        res = res + [trySlice(start, stop, step)]

        self.equivalentEvaluationTest(f)

    def test_string_getitem_exhaustive_2(self):
        def f():
            x = "asd"
            def trySlice(start, stop):
                try:
                    return ("OK", x[start:stop])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            sz = len(x)
            values = range(-sz, sz) + [None, sz - 10, sz + 10]

            res = []
            for start in values:
                for stop in values:
                    res = res + [trySlice(start, stop)]

            return res

        self.equivalentEvaluationTest(f)


    def test_string_getitem_exhaustive_3(self):
        def f():
            x = "asd"
            def tryGetItem(ix):
                try:
                    return ("OK", x[ix])
                except Exception as e:
                    if isinstance(e, ValueError):
                        return "ValueError"
                    elif isinstance(e, IndexError):
                        return "IndexError"
                    elif isinstance(e, TypeError):
                        return "TypeError"
                    raise e

            sz = len(x)
            indices = range(-sz, sz) + [sz - 10, sz + 10, 1.0, None]

            res = []
            for ix in indices:
                res = res + [tryGetItem(ix)]

            return res

        self.equivalentEvaluationTest(f)


    def test_socket_io_disconnect(self):
        def f():
            s = 0
            for i in xrange(100000000):
                s = s + ((i-1)/(i+1))**2
            return s

        with self.create_executor() as executor:
            future = executor.submit(f)
            socketInterface = executor.connection.webObjectFactory.jsonInterface
            socketInterface.disconnect()
            with self.assertRaises(pyfora.PyforaError) as cm:
                future.result()

            error_content = cm.exception.message
            self.assertEqual(error_content['responseType'], 'Failure')
            self.assertEqual(error_content['message'], 'Disconnected from server')


    def test_file_read(self):
        with self.create_executor() as executor:
            remote = executor.importRemoteFile('/etc/hosts').result()
            local = remote.toLocal().result()
            self.assertIn('127.0.0.1', local)


    def test_file_read_bad_path(self):
        with self.create_executor() as executor:
            with self.assertRaises(pyfora.PyforaError):
                executor.importRemoteFile('/foo/bar.baz').result()

