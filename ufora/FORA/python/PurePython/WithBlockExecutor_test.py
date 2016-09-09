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

import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.Exceptions as Exceptions
import pyfora.pure_modules.pure_pandas as PurePandas
import time

import unittest
import traceback
import pandas


class WithBlockExecutors_test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executor = None

    @classmethod
    def tearDownClass(cls):
        if cls.executor is not None:
            cls.executor.close()

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return InMemorySimulationExecutorFactory.create_executor()
        if cls.executor is None:
            cls.executor = InMemorySimulationExecutorFactory.create_executor()
            cls.executor.stayOpenOnExit = True
        return cls.executor

    def equivalentEvaluationTest(self, func, *args):
        if len(args) == 0:
            self.equivalentEvaluationTestNoArgs(func)
        elif len(args) == 1:
            self.equivalentEvaluationTestOneArg(func, args[0])
        else:
            assert False, "don't know how to handle more than 1 arg, since we can't translate *args yet"

    def equivalentEvaluationTestOneArg(self, func, arg):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                res = func(arg)
            self.assertEqual(res.toLocal().result(), func(arg))

    def equivalentEvaluationTestNoArgs(self, func):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                res = func()
            self.assertEqual(res.toLocal().result(), func())

    def test_with_block_assignment_1(self):
        with self.create_executor() as fora:
            x = 5

            with fora.remotely:
                b = 4 + x

            result = b.toLocal().result()
            self.assertEqual(result, 9)

    def test_with_block_assignment_2(self):
        with self.create_executor() as fora:
            with fora.remotely:
                b = 4 + 5
                ix = b + 2

            b_result = b.toLocal().result()
            self.assertEqual(b_result, 9)

            ix_result = ix.toLocal().result()
            self.assertEqual(ix_result, 11)

    def test_using_time_within_with_block(self):
        with self.create_executor() as fora:
            with fora.remotely:
                t0 = time.time()
                res = sum(x for x in xrange(10**9))
                if res is not None:
                    elapsed = time.time() - t0


        self.assertTrue(elapsed > 1.0)

    def test_printing_in_with_block_1(self):
        with self.create_executor() as fora:
            messages = []
            def logMessageHandler(msg):
                if not msg['isDeveloperFacing']:
                    messages.append(msg['message'])

            fora.connection.logMessageHandler = logMessageHandler

            with fora.remotely:
                print 1, sum(x for x in xrange(10**9))
                print 2, sum(x for x in xrange(10**9))
                print 3, sum(x for x in xrange(10**9))
                print 4, sum(x for x in xrange(10**9))

            t0 = time.time()
            while len(messages) < 4 and time.time() - t0 < 10:
                time.sleep(1.0)

        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[0][:2], "1 ")
        self.assertEqual(messages[1][:2], "2 ")
        self.assertEqual(messages[2][:2], "3 ")
        self.assertEqual(messages[3][:2], "4 ")

    def test_printing_in_with_block_2(self):
        with self.create_executor() as fora:
            messages = []
            def logMessageHandler(msg):
                if not msg['isDeveloperFacing']:
                    messages.append(msg['message'])

            fora.connection.logMessageHandler = logMessageHandler

            with fora.remotely:
                def f(x):
                    print x,
                    return x

                print sum(f(x) for x in xrange(100))

            t0 = time.time()
            while len(messages) < 101 and time.time() - t0 < 12:
                time.sleep(1.0)

            self.assertEqual(len(messages), 101)

    def test_with_block_reassignments(self):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                ix = 0
                while ix < 10:
                    b = ix
                    ix = ix + 1

            b_result = b.toLocal().result()
            self.assertEqual(b_result, 9)

            ix_result = ix.toLocal().result()
            self.assertEqual(ix_result, 10)

    def test_with_block_complicated_function(self):
        fora = self.create_executor()
        with fora:
            y = 1
            z = 2
            w = 3
            def h(x):
                return w + 2 * x
            def f(x):
                if x < 0:
                    return x
                return y + g(x - 1) + h(x)
            def g(x):
                if x < 0:
                    return x
                return z * f(x - 1) + h(x - 1)
            arg = 4
            with fora.remotely:
                result = f(arg)

            self.assertEqual(result.toLocal().result(), f(arg))

    def test_with_block_return_list_len(self):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                l = []
                ix = 0
                while ix < 1000000:
                    l = l + [ix]
                    ix = ix + 1
                l = len(l)

            self.assertEqual(l.toLocal().result(), 1000000)

    def test_with_block_return_list_and_rereference_in_second_block(self):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                l = []
                ix = 0
                while ix < 100:
                    l = l + [ix]
                    ix = ix + 1

            with fora.remotely:
                l2 = len(l)

            self.assertEqual(l2.toLocal().result(), 100)

    def test_with_block_tuple_proxies(self):
        fora = self.create_executor()
        with fora:
            def f():
                return (1,2,3)

            res = fora.submit(f).result()
            proxies = res.toTupleOfProxies().result()
            results = tuple(p.toLocal().result() for p in proxies)

            self.assertEqual(results, (1,2,3))

    def test_with_block_dict_proxies(self):
        fora = self.create_executor()
        with fora:
            def f():
                return {'1':1,'2':2,'3':3}

            res = fora.submit(f).result()
            proxies = res.toDictOfAssignedVarsToProxyValues().result()
            results = {k:v.toLocal().result() for k,v in proxies.iteritems()}

            self.assertEqual(results, {'1':1,'2':2,'3':3})

    def test_with_block_download_policy(self):
        fora = self.create_executor()
        with fora:
            with fora.remotely.remoteAll():
                x = 1

            self.assertIsInstance(x, RemotePythonObject.ComputedRemotePythonObject)

            with fora.remotely.downloadAll():
                x = 2

            self.assertIsInstance(x, int)

            with fora.remotely.downloadSmall(1000):
                smallString = "asdf"
                largeString = smallString

                while len(largeString) < 10000:
                    largeString = largeString + largeString

            self.assertIsInstance(smallString, str)
            self.assertIsInstance(largeString, RemotePythonObject.ComputedRemotePythonObject)


    def test_with_block_exception_in_with_block(self):
        fora = self.create_executor()
        with fora:
            try:
                with fora.remotely:
                    def f():
                        raise UserWarning("message")

                    def g():
                        f()

                    def h():
                        g()

                    h()

                    x = 30

                #we shouldn't get here
                self.assertFalse(True, "We should have raised an exception")
            except UserWarning as e:
                self.assertEqual(e.message, "message")
                tracebackFormatted = traceback.format_exc()

                #verify some properties of the stacktrace
                self.assertTrue('f()' in tracebackFormatted)
                self.assertTrue('g()' in tracebackFormatted)
                self.assertTrue('h()' in tracebackFormatted)
                self.assertTrue('raise UserWarning("message")' in tracebackFormatted)


    """
    This blows up inside

    def test_with_block_return_list_and_rereference_in_second_block(self):
        fora = self.create_executor()
        with fora:
            with fora.remotely:
                l = []
                ix = 0
                while ix < 100:
                    l = l + [ix]
                    ix = ix + 1

            lAndZero = (l,0)
            with fora.remotely:
                l2 = len(lAndZero[0])

            self.assertEqual(l2.toLocal().result(), 100)
    """

    def test_with_block_assigned_vars_and_exceptions_1(self):
        with self.create_executor() as fora:
            try:
                with fora.remotely:
                    a = 0
                    b = 1
                    raise UserWarning("omg")
                    c = 2
                    d = 3
            except UserWarning as e:
                pass

            self.assertEqual(a.toLocal().result(), 0)
            self.assertEqual(b.toLocal().result(), 1)
            with self.assertRaises(UnboundLocalError):
                c
            with self.assertRaises(UnboundLocalError):
                d

    def test_with_block_assigned_vars_and_exceptions_2(self):
        with self.create_executor() as fora:
            try:
                with fora.remotely:
                    a = 0
                    b = 1
                    for ix in range(10):
                        b = b + 1
                    raise UserWarning("omg")
                    c = 2
                    d = 3
            except UserWarning as e:
                pass

            self.assertEqual(a.toLocal().result(), 0)
            self.assertEqual(b.toLocal().result(), 11)

            self.assertEqual(ix.toLocal().result(), 9)

            with self.assertRaises(UnboundLocalError):
                c
            with self.assertRaises(UnboundLocalError):
                d

    def test_with_block_assign_to_invalid_var(self):
        with self.create_executor() as fora:
            x = 10
            with fora.remotely:
                if x < 20:
                    a = 0
                else:
                    b = 0

            self.assertEqual(a.toLocal().result(), 0)

            with self.assertRaises(UnboundLocalError):
                b

    def test_with_block_conditionally_assign_to_already_assigned_var_1(self):
        with self.create_executor() as fora:
            x = 10
            y = 10
            z = 100
            with fora.remotely.downloadAll():
                if x < 20:
                    x = x + z
                else:
                    y = y + z

            self.assertEqual(x, 110)
            self.assertEqual(y, 10)

    def test_with_block_conditionally_assign_to_already_assigned_var_2(self):
        with self.create_executor() as fora:
            x = 10
            z = 100
            with fora.remotely.downloadAll():
                if x < 20:
                    x = x + z
                else:
                    y = y + z

            self.assertEqual(x, 110)

            with self.assertRaises(UnboundLocalError):
                y

    def test_with_block_more_assignments(self):
        with self.create_executor() as fora:
            with fora.remotely:
                x = 0
                for ix in xrange(10):
                    x = x + 1

            self.assertEqual(x.toLocal().result(), 10)

            # doesn't work
            # self.assertEqual(ix.toLocal().result(), 10)

    def test_with_block_divide_by_zero_throws_ZeroDivisionError(self):
        with self.create_executor() as fora:
            with self.assertRaises(ZeroDivisionError):
                with fora.remotely:
                    x = 1 / 0

    def test_with_block_swallows_print_statement(self):
        with self.create_executor() as fora:
            with fora.remotely:
                x = "this is ok"
                y = "this is still ok"
                print "this shouldn't work"


    def test_with_block_invalid_conversion_throws(self):
        with self.create_executor() as fora:
            with self.assertRaises(Exceptions.InvalidPyforaOperation):
                with fora.remotely:
                    x = "this is ok"
                    y = "this is still ok"
                    #this will blow up
                    y[0] = 10

    def test_with_block_list_append_throws_reasonable_exception(self):
        with self.create_executor() as fora:
            with self.assertRaises(Exceptions.InvalidPyforaOperation):
                with fora.remotely:
                    [].append(10)

    def test_with_block_return_in_with_block_throws(self):
        with self.create_executor() as fora:
            with self.assertRaises(Exceptions.BadWithBlockError):
                with fora.remotely:
                    x = 3
                    y = 4
                    return x + y

    def with_block_generator(self):
        with self.create_executor() as fora:
            with fora.remotely:
                x = 1
                y = 2
                yield x + y

    def test_with_block_yield_in_with_block_throws(self):
        with self.assertRaises(Exceptions.BadWithBlockError):
            for _ in self.with_block_generator():
                pass

    def test_with_block_return_and_yield_nested_in_with_block_dont_throw(self):
        with self.create_executor() as fora:
            with fora.remotely:
                def zero():
                    return 0
                def zeroGen():
                    yield 0
                x = zero()
                y = zeroGen()

    def test_with_block_reassignment_in_separate_with_block(self):
        with self.create_executor() as fora:
            ctx = fora.remotely.downloadAll()
            with ctx:
                x = 1

            self.assertEqual(x, 1)

            with ctx:
                x = x + 1

            self.assertEqual(x, 2)

    def test_repeated_instance(self):
        with self.create_executor() as fora:
            with fora.remotely:
                df = PurePandas.PurePythonDataFrame([[1,2,3], [4,5,6]])
                res1 = isinstance(df, PurePandas.PurePythonDataFrame)
                res2 = isinstance(df, pandas.DataFrame)

            self.assertEqual(res1.toLocal().result(), True)
            self.assertEqual(res2.toLocal().result(), False)
            self.assertIsInstance(df.toLocal().result(), pandas.DataFrame)

            with fora.remotely:
                res3 = isinstance(df, PurePandas.PurePythonDataFrame)
                res4 = isinstance(df, pandas.DataFrame)
                type_ = type(df)

            self.assertEqual(res4.toLocal().result(), False)
            self.assertEqual(res3.toLocal().result(), True, type_.toLocal().result())

    def test_with_block_executor_corecounts(self):
        maxCores = [0]
        def setMaxCores(cores):
            maxCores[0] = max(maxCores[0], cores)

        with self.create_executor() as fora:
            with fora.remotely.withStatusCallback(setMaxCores):
                res = sum(float(x) for x in xrange(10000000000))

            self.assertTrue(maxCores[0] > 1)

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])

