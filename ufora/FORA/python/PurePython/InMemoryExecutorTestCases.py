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
import os
import ufora.FORA.python.PurePython.ExecutorTestCases as ExecutorTestCases
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

class InMemoryExecutorTestCases(ExecutorTestCases.ExecutorTestCases):
    def test_list_hashing(self):
        def f(x):
            x = x[0]
            res = 0
            while x > 0:
                x = x - 1
                res = res + x
            return res

        t0 = time.time()
        self.evaluateWithExecutor(f, [1000000000])
        t1 = time.time()
        self.evaluateWithExecutor(f, [1000000001])
        t2 = time.time()
        self.evaluateWithExecutor(f, [1000000000])
        t3 = time.time()

        firstPass = t1 - t0
        secondPass = t2 - t1
        thirdPass = t3 - t2

        #the third pass should be _way_ faster.
        self.assertTrue(thirdPass / firstPass < .1)
        self.assertTrue(thirdPass / secondPass < .1)

    def test_list_comprehension_perf(self):
        def f(totalCt):
            return sum([sum([x for x in xrange(ct)]) for ct in xrange(totalCt)])

        self.evaluateWithExecutor(f, 3000)

        @PerformanceTestReporter.PerfTest("pyfora.NestedListComprehension")
        def runTest():
            self.evaluateWithExecutor(f, 3001)

        runTest()



    def test_class_identities(self):
        class IdentClass:
            def __init__(self, a,b,e,c,d):
                self.a=a
                self.d=d
                self.e=e
                self.e=e+1.0
                self.b=b
                self.c=c

        inst = IdentClass(1,2,3,4,5)

        def getMembers(inst):
            return __inline_fora(
                """fun(@unnamed_args:(x), *args) {
                       PyString(String(x.@m))
                       }"""
                )(inst)

        with self.create_executor() as ufora:
            with ufora.remotely.downloadAll():
                inst2 = IdentClass(1,2,3,4,5)
                shouldBeTrue = type(inst) is type(IdentClass(1,2,3,4,5))
                shouldBeTrue2 = type(inst2) is type(IdentClass(1,2,3,4,5))
                shouldBeTrue3 = type(inst) is IdentClass
                shouldBeTrue4 = type(inst2) is IdentClass
                shouldBeTrue5 = inst is inst2

                instMembs = getMembers(inst)
                instMembs2 = getMembers(inst2)

        self.assertEqual(instMembs, instMembs2)

        self.assertTrue(shouldBeTrue)
        self.assertTrue(shouldBeTrue2)
        self.assertTrue(shouldBeTrue3)
        self.assertTrue(shouldBeTrue4)
        self.assertTrue(shouldBeTrue5)

    def test_classInstIsInstance(self):
        class X:
            def dot(self, other):
                return dot_(self, other)

        def dot_(self, other):
            return X

        with self.create_executor() as ufora:
            with ufora.remotely:
                a = X()

            b = X()

            with ufora.remotely.downloadAll():
                c = X()

                res = (isinstance(a, X), isinstance(b, X), isinstance(c, X))

            self.assertEqual(res, (True,True,True))

    def test_with_blocks_inside_converted_code(self):
        with self.assertRaises(pyfora.InvalidPyforaOperation):
            with self.create_executor() as executor:
                with executor.remotely:
                    with 10:
                        X = 10

    def test_pyfora_pass_future_into_with_block_works(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            payload = "this is some data"
            s3().setKeyValue("bucketname", "key", payload)

            remote = executor.importS3Dataset("bucketname", "key")

            with executor.remotely.downloadAll():
                res = len(remote)

            assert res == len(payload)

    def test_pyfora_s3_read(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            payload = "this is some data"
            s3().setKeyValue("bucketname", "key", payload)

            remote = executor.importS3Dataset("bucketname", "key").result()
            remoteResult = remote.toLocal().result()
            self.assertEqual(payload, remoteResult)

            assert s3 is not None

    def test_pyfora_s3_read_bad_bucket(self):
        with self.create_executor() as executor:
            with self.assertRaises(pyfora.ComputationError):
                result = executor.importS3Dataset("no_such_bucket", "key").result()
                result.toLocal().result()

    def test_pyfora_s3_read_bad_key(self):
        with self.create_executor() as executor:
            s3 = self.getS3Interface(executor)
            payload = "this is some data"
            s3().setKeyValue("bucketname", "key", payload)

            with self.assertRaises(pyfora.ComputationError):
                result = executor.importS3Dataset("bucketname", "no such key").result()
                result.toLocal().result()


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

        t0 = time.time()
        ct = 0
        while ct < 100:
            fora.submit(add, 1, 2).result().toLocal().result()
            ct += 1
        self.assertTrue(time.time() - t0 < 4.0)

    def test_repeated_evaluation_1(self):
        with self.create_executor() as executor:
            def add(x, y):
                return x + y

            res = executor.submit(add, 1, 2).result().toLocal().result()
            res = executor.submit(add, 1, 2).result().toLocal().result()

            self.assertEqual(res, add(1,2))
        
    def test_repeated_evaluation_2(self):
        with self.create_executor() as executor:
            def f(arg, func1, func2):
                return func1(func2(arg))

            def h(x):
                return x + 1
            def g(x):
                return h(x)

            y = 1

            res = executor.submit(f, y, h, g).result().toLocal().result()
            res = executor.submit(f, y, h, g).result().toLocal().result()
            res = executor.submit(f, y, h, g).result().toLocal().result()
            
            self.assertEqual(res, f(y, h, g))

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

    def test_exceptions_in_list_comprehensions_stable(self):
        def isPrime(p):
            if p == 900001:
                raise UserWarning("This is an exception")
            x = 2
            while x*x <= p:
                if p%x == 0:
                    return 0
                x=x+1
            return 1

        def f(ct):
            return sum([isPrime(x) for x in xrange(ct)])

        def getATrace(ct):
            with self.create_executor() as fora:
                try:
                    c = fora.submit(f, ct).result().toLocal().result()
                except Exception as e:
                    return e.trace

        t1 = getATrace(1000000)

        file_ = __file__
        if file_[-4:] == ".pyc":
            file_ = __file__[:-1]

        for x in t1:
            self.assertEqual(x['path'][0], os.path.abspath(file_))
        self.assertEqual(t1, getATrace(1000001))
        self.assertEqual(t1, getATrace(1000002))
        self.assertEqual(t1, getATrace(1000003))

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

