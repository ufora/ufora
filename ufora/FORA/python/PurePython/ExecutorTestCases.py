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

import pyfora
import pyfora.PyAstUtil as PyAstUtil
import numpy
import logging
import traceback
import time
import ufora.FORA.python.PurePython.EquivalentEvaluationTestCases as EquivalentEvaluationTestCases
import ufora.FORA.python.PurePython.ExceptionTestCases as ExceptionTestCases

import random

class ExecutorTestCases(
            EquivalentEvaluationTestCases.EquivalentEvaluationTestCases,
            ExceptionTestCases.ExceptionTestCases
            ):
    """ExecutorTestCases - mixin to define test cases for the pyfora Executor cass."""

    def create_executor(self, allowCached=True):
        """Subclasses of the test harness should implement"""
        raise NotImplementedError()

    def evaluateWithExecutor(self, func, *args, **kwds):
        shouldClose = True
        if 'executor' in kwds:
            executor = kwds['executor']
            shouldClose = False
        else:
            executor = self.create_executor()

        try:
            func_proxy = executor.define(func).result()
            args_proxy = [executor.define(a).result() for a in args]
            res_proxy = func_proxy(*args_proxy).result()

            result = res_proxy.toLocal().result()
            return result
        except Exception as ex:
            raise ex
        finally:
            if shouldClose:
                executor.__exit__(None, None, None)


    @staticmethod
    def defaultComparison(x, y):
        if isinstance(x, basestring) and isinstance(y, basestring):
            return x == y

        if hasattr(x, '__len__') and hasattr(y, '__len__'):
            l1 = len(x)
            l2 = len(y)
            if l1 != l2:
                return False
            for idx in range(l1):
                if not ExecutorTestCases.defaultComparison(x[idx], y[idx]):
                    return False
            return True
        else:
            return x == y and type(x) is type(y)

    def equivalentEvaluationTest(self, func, *args, **kwds):
        comparisonFunction = ExecutorTestCases.defaultComparison
        if 'comparisonFunction' in kwds:
            comparisonFunction = kwds['comparisonFunction']

        with self.create_executor() as executor:
            t0 = time.time()
            func_proxy = executor.define(func).result()
            args_proxy = [executor.define(a).result() for a in args]
            res_proxy = func_proxy(*args_proxy).result()

            pyforaResult = res_proxy.toLocal().result()
            t1 = time.time()
            pythonResult = func(*args)
            t2 = time.time()

            self.assertTrue(
                comparisonFunction(pyforaResult, pythonResult), 
                "Pyfora and python returned different results: %s != %s for %s(%s)" % (pyforaResult, pythonResult, func, args)
                )

            if t2 - t0 > 5.0:
                print "Pyfora took ", t1 - t0, ". python took ", t2 - t1

        return pythonResult

    def test_string_indexing(self):
        def f():
            a = "abc"
            return (a[0], a[1], a[2], a[-1], a[-2])
        self.equivalentEvaluationTest(f)

    def test_string_indexing_2(self):
        def f(idx):
            x = "asdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdfasdf"
            return x[idx]

        self.equivalentEvaluationTest(f, -1)
        self.equivalentEvaluationTest(f, -2)
        self.equivalentEvaluationTest(f, 0)
        self.equivalentEvaluationTest(f, 1)

    def test_class_pass(self):
        def f():
            class X:
                pass

        self.equivalentEvaluationTest(f)

    def test_string_comparison(self):
        def f():
            a = "a"
            b = "b"
            r1 = a < b
            r2 = a > b
            return (r1, r2)

        self.equivalentEvaluationTest(f)

    def test_string_duplication(self):
        def f():
            a = "asdf"
            r1 = a * 20
            r2 = 20 * a
            return (r1, r2)

        self.equivalentEvaluationTest(f)

    def test_range_builtin_simple(self):
        def f(x):
            return range(x)

        self.equivalentEvaluationTest(f, 10)

    def test_xrange_builtin_simple(self):
        def f(x):
            toReturn = 0
            for ix in xrange(x):
                toReturn = ix + toReturn
            return toReturn
        self.equivalentEvaluationTest(f, 10)

    def test_range_builtin_overloads(self):
        def f(start, stop, incr=1):
            return range(start, stop, incr)

        self.equivalentEvaluationTest(f, 1, 10)
        self.equivalentEvaluationTest(f, 10, 5)
        self.equivalentEvaluationTest(f, 5, 10)
        self.equivalentEvaluationTest(f, 10, 1, 2)
        self.equivalentEvaluationTest(f, 10, 5, 5)
        self.equivalentEvaluationTest(f, 10, 10, 10)

    def equivalentEvaluationTestThatHandlesExceptions(self, func, *args):
        with self.create_executor() as executor:
            try:
                pythonResult = func(*args)
                pythonSucceeded = True
            except Exception as ex:
                pythonSucceeded = False

            try:
                pyforaResult = self.evaluateWithExecutor(func, *args, executor=executor)
                pyforaSucceeded = True
            except pyfora.Exceptions.ComputationError as ex:
                if pythonSucceeded:
                    logging.error("Python succeeded, but pyfora threw %s for %s%s", ex, func, args)
                pyforaSucceeded = False
            except:
                logging.error("General exception in pyfora for %s%s:\n%s", func, args, traceback.format_exc())
                return False

            self.assertEqual(pythonSucceeded, pyforaSucceeded,
                    "Pyfora and python returned successes: %s%s" % (func, args)
                    )

            if pythonSucceeded:
                self.assertEqual(pythonResult, pyforaResult, 
                    "Pyfora and python returned different results: %s != %s for %s%s" % (pyforaResult, pythonResult, func, args)
                    )
                return pythonResult

    def resolvedFutures(self, futures):
        results = [f.result() for f in futures]
        localResults = [r.toLocal() for r in results]
        foraResults = []
        for f in localResults:
            try:
                foraResults.append(f.result())
            except Exception as e:
                pass
        return foraResults

    def test_ord_chr_builtins(self):
        def f():
            chars = [chr(val) for val in range(40, 125)]
            vals = [ord(val) for val in chars]
            return (chars, vals)

        r = self.equivalentEvaluationTest(f)

    def test_python_if_int(self):
        def f():
            if 1:
                return True
            else:
                return False
        self.equivalentEvaluationTest(f)

    def test_python_if_int_2(self):
        def f2():
            if 0:
                return True
            else:
                return False
        self.equivalentEvaluationTest(f2)

    def test_python_and_or(self):
        def f():
            return (
                0 or 1,
                1 or 2,
                1 or 0,
                0 or False,
                1 or 2 or 3,
                0 or 1,
                0 or 1 or 2,
                1 and 2,
                0 and 1,
                1 and 0,
                0 and False,
                1 and 2 and 3,
                0 and 1 and 2,
                1 and 2 and 0,
                1 and 0 and 2,
                0 and False and 2
                )

        self.equivalentEvaluationTest(f)

    def test_string_equality_methods(self):
        def f():
            a = "val1"
            b = "val1"
            r1 = a == b
            r2 = a != b
            a = "val2"
            r3 = a == b
            r4 = a != b
            r5 = a.__eq__(b)
            r6 = a.__ne__(b)
            return (r1, r2, r3, r4, r5, r6)

        self.equivalentEvaluationTest(f)

    def test_nested_function_arguments(self):
        def c(v1, v2):
            return v1 + v2
        def b(v, f):
            return f(v, 8)
        def a(v):
            return b(v, c)

        self.equivalentEvaluationTest(a, 10)

    def test_default_arguments_1(self):
        def f(a=None):
            return a

        self.equivalentEvaluationTest(f, 0)
        self.equivalentEvaluationTest(f, None)
        self.equivalentEvaluationTest(f, -3.3)
        self.equivalentEvaluationTest(f, "testing")

    def test_default_arguments_2(self):
        def f(a, b=1, c=None):
            return (a, b, c)

        self.equivalentEvaluationTest(f, 0, None)
        self.equivalentEvaluationTest(f, None, 2)
        self.equivalentEvaluationTest(f, None, "test")
        self.equivalentEvaluationTest(f, -3.3)
        self.equivalentEvaluationTest(f, "test", "test")

    def test_handle_empty_list(self):
        def f():
            return []
        self.equivalentEvaluationTest(f)

    def test_zero_division_should_throw(self):
        def f1():
            return 4 / 0

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f1)

        def f2():
            return 4.0 / 0

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f2)

        def f3():
            return 4 / 0.0

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f3)

        def f4():
            return 4.0 / 0.0

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f4)

    def test_builtins_abs(self):
        def f(x):
            return abs(x)
        for x in range(-10, 10):
            self.equivalentEvaluationTest(f, x)

        self.equivalentEvaluationTest(f, True)
        self.equivalentEvaluationTest(f, False)
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, [])
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, ["test"])
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, "test")

    def test_builtins_all(self):
        def f(x):
            return all(x)
        self.equivalentEvaluationTest(f, [])
        self.equivalentEvaluationTest(f, [True])
        self.equivalentEvaluationTest(f, [True, True])
        self.equivalentEvaluationTest(f, [True, False])
        self.equivalentEvaluationTest(f, [False, True])
        self.equivalentEvaluationTest(f, [False, False])

    def test_large_strings(self):
        def f():
            a = "val1"

            while len(a) < 1000000:
                a = a + a

            return a

        self.equivalentEvaluationTest(f)

    def test_numpy(self):
        n = numpy.zeros(10)
        def f():
            return n.shape
        self.equivalentEvaluationTest(f)

    def test_primitive_type_comparisons(self):
        def f():
            toReturn = []
            toCompare = [True, False, 0, 1, 2, 0.0, 1.0, 2.0, -1, -1.1, "test", []]
            l = len(toCompare)
            for idx1 in range(l):
                for idx2 in range(l):
                    a = toCompare[idx1]
                    b = toCompare[idx2]
                    toReturn = toReturn + [a < b]
                    toReturn = toReturn + [a > b]
                    toReturn = toReturn + [a <= b]
                    toReturn = toReturn + [a >= b]
            return toReturn
        r = self.equivalentEvaluationTest(f)

    def test_return_numpy(self):
        n = numpy.zeros(10)
        def f():
            return n
        res = self.evaluateWithExecutor(f)

        self.assertTrue(isinstance(res, numpy.ndarray), res)

        self.equivalentEvaluationTest(f)

    def test_len_on_tuple(self):
        def f():
            a = (9,)
            b = ()
            c = (1,2,4)
            return (len(a), len(b), len(c))
        res = self.evaluateWithExecutor(f)

    def test_reversed_builtins(self):
        def f():
            a = [1, 2, 3, 4, 5, 6]
            b = reversed(a)
            toReturn = []
            for v in b:
                toReturn = toReturn + [v]
            return toReturn

        r = self.equivalentEvaluationTest(f)

    def test_reduce_builtin(self):
        toReduce = []
        for _ in range(10):
            toReduce.append(random.uniform(-10, 10))
        def f():
            return reduce(lambda x, y: x * y, toReduce)
        r = self.equivalentEvaluationTest(f)

    def test_return_list(self):
        def f():
            return [1,2,3,4,5]

        self.equivalentEvaluationTest(f)

    def test_list_in_loop(self):
        def f(ct):
            ix = 0
            l = []
            while ix < ct:
                l = l + [ix]
                ix = ix + 1

            res = 0
            for e in l:
                res = res + e
            return res

        ct = 1000000
        res = self.evaluateWithExecutor(f, ct)
        self.assertEqual(res, ct * (ct-1)/2)

    def test_list_getitem_1(self):
        def f():
            l = [1,2,3]

            return l[0]

        self.equivalentEvaluationTest(f)

    def test_list_getitem_2(self):
        v = [1,2,3]
        def f(ix):
            return v[ix]

        for ix in range(-3,3):
            self.equivalentEvaluationTest(f,ix)

    def test_list_getitem_3(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.equivalentEvaluationTest(nestedLists)

    def test_list_len(self):
        def f():
            l = [1,2,3]

            return (len(l), len(l) == 3, len(l) is 3)

        self.equivalentEvaluationTest(f)

    def test_lists_3(self):
        def f(elt):
            x = [1,2,3]
            return x.index(elt)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)

    def test_lists_6(self):
        v = [1,2,3]
        def f(val):
            return v.index(val)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)

    def test_tuple_conversion(self):
        def f(x):
            return (x,x+1)

        self.equivalentEvaluationTest(f, 10)

    def test_tuples_1(self):
        tup = (1, 2, 3)

        def f(ix):
            return tup[ix]
        
        for ix in range(-3, 3):
            self.equivalentEvaluationTest(f, ix)
            
    def test_len(self):
        def f(x):
            return len(x)

        self.equivalentEvaluationTest(f, "asdf")

    def test_TrueFalseNone(self):
        def f():
            return (True, False, None)

        self.equivalentEvaluationTest(f)

    def test_returns_len(self):
        def f():
            return len

        res = self.evaluateWithExecutor(f)
        self.assertIs(res, f())

    def test_returns_str(self):
        def f():
            return str

        res = self.evaluateWithExecutor(f)
        self.assertIs(str, f())

    def test_str_on_class(self):
        def f():
            class StrOnClass:
                def __str__(self):
                    return "special"
            return str(StrOnClass())

        self.equivalentEvaluationTest(f)

    def test_define_constant(self):
        x = 4
        with self.create_executor() as executor:
            define_x = executor.define(x)
            fora_x = define_x.result()
            self.assertIsNotNone(fora_x)

    def test_define_calculation_on_prior_value(self):
        x = 4
        with self.create_executor() as executor:
            fora_x = executor.define(x).result()

            def f(x):
                return x + 1

            fora_f = executor.define(f).result()

            fora_f_of_x = fora_f(fora_x).result()

            fora_f_of_f_of_x = fora_f(fora_f_of_x).result()

            self.assertEqual(fora_f_of_f_of_x.toLocal().result(), 6)

    def test_define_calculation_on_prior_defined_value_in_closure(self):
        x = 4
        with self.create_executor() as executor:
            fora_x = executor.define(x).result()

            def f():
                return fora_x + 1

            fora_f = executor.define(f).result()

            self.assertEqual(fora_f().result().toLocal().result(), 5)

    def test_define_calculation_on_prior_calculated_value_in_closure(self):
        x = 4
        with self.create_executor() as executor:
            fora_x = executor.define(x).result()

            def f(x):
                return fora_x + 1

            fora_f = executor.define(f).result()

            fora_f_x = fora_f(fora_x).result()

            def f2():
                return fora_f_x + 1

            fora_f2 = executor.define(f2).result()

            self.assertEqual(fora_f2().result().toLocal().result(), 6)

    def test_define_constant_string(self):
        x = "a string"
        with self.create_executor() as executor:
            define_x = executor.define(x)
            fora_x = define_x.result()
            self.assertIsNotNone(fora_x)

    def test_compute_string(self):
        def f():
            return "a string"

        remote = self.evaluateWithExecutor(f)
        self.assertEqual(f(), remote)
        self.assertTrue(isinstance(remote, str))

    def test_compute_float(self):
        def f():
            return 1.5

        remote = self.evaluateWithExecutor(f)
        self.assertEqual(f(), remote)
        self.assertTrue(isinstance(remote, float))

    def test_compute_nothing(self):
        def f():
            return None

        remote = self.evaluateWithExecutor(f)
        self.assertIs(f(), remote)

    def test_define_function(self):
        def f(x):
            return x+1
        arg = 4

        with self.create_executor() as executor:
            f_proxy = executor.define(f).result()
            arg_proxy = executor.define(arg).result()

            res_proxy = f_proxy(arg_proxy).result()
            self.assertEqual(res_proxy.toLocal().result(), 5)

    def test_class_member_functions(self):
        class ClassTest0:
            def __init__(self,x):
                self.x = x

            def f(self):
                return 10

        def testFun():
            c = ClassTest0(10)
            return c.x

        self.equivalentEvaluationTest(testFun)

    def test_list_bound_methods_know_they_are_pyfora(self):
        def testFun():
            return [].__add__.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))

    def test_primitives_know_they_are_pyfora(self):
        def testFun():
            x = 10
            return x.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))

    def test_class_objects_know_they_are_pyfora(self):
        class ClassTest3:
            def __init__(self):
                pass

        def testFun():
            return ClassTest3.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))

    def test_classes_know_they_are_pyfora(self):
        class ClassTest2:
            def __init__(self):
                pass

        def testFun():
            c = ClassTest2()
            return c.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))

    def test_class_member_semantics(self):
        def f():
            return 'free f'

        y = 'free y'

        class ClassTest1:
            def __init__(self, y):
                self.y = y

            def f(self):
                return ('member f', y, self.y)

            def g(self):
                return (f(), self.f())

        def testFun():
            c = ClassTest1('class y')
            return c.g()

        self.equivalentEvaluationTest(testFun)

    def test_repeatedEvaluation(self):
        def f(x):
            return x+1
        arg = 4

        for _ in range(10):
            with self.create_executor() as executor:
                f_proxy = executor.define(f).result()
                arg_proxy = executor.define(arg).result()

                res_proxy = f_proxy(arg_proxy).result()
                self.assertEqual(res_proxy.toLocal().result(), f(arg))

    def test_returnClasses(self):
        class ReturnedClass:
            def __init__(self, x):
                self.x = x

        def f(x):
            return ReturnedClass(x)

        shouldBeReturnedClass = self.evaluateWithExecutor(f, 10)

        self.assertEqual(shouldBeReturnedClass.x, 10)
        self.assertEqual(str(shouldBeReturnedClass.__class__), str(ReturnedClass))


    def test_returnFunctions(self):
        y = 2
        def toReturn(x):
            return x * y

        def f():
            return toReturn

        shouldBeToReturn = self.evaluateWithExecutor(f)

        self.assertEqual(shouldBeToReturn(10), toReturn(10))
        self.assertEqual(str(shouldBeToReturn.__name__), str(toReturn.__name__))
        self.assertEqual(PyAstUtil.getSourceText(shouldBeToReturn), PyAstUtil.getSourceText(toReturn))

    def test_returnClassObject(self):
        class ReturnedClass2:
            @staticmethod
            def f():
                return 10

        def f():
            return ReturnedClass2

        def comparisonFunction(pyforaVal, pythonVal):
            return pyforaVal.f() == pythonVal.f()

        self.equivalentEvaluationTest(f, comparisonFunction=comparisonFunction)

    def test_returnDict(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f():
            return x

        self.equivalentEvaluationTest(f, comparisonFunction=lambda x, y: x == y)

    def test_returnClassObjectWithClosure(self):
        x = 10
        class ReturnedClass3:
            def f(self, y):
                return x + y

        def f():
            return ReturnedClass3

        def comparisonFunction(pyforaVal, pythonVal):
            return pyforaVal().f(10) == pythonVal().f(10)

        self.equivalentEvaluationTest(f, comparisonFunction=comparisonFunction)

    def test_define_complicated_function(self):
        with self.create_executor() as executor:
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
            res_proxy = executor.submit(f, arg).result()
            self.assertEqual(res_proxy.toLocal().result(), f(arg))


    def test_cancellation(self):
        with self.create_executor() as executor:
            def f(x):
                i = 0
                while i < x:
                    i = i + 1
                return i
            arg = 100000000000

            future = executor.submit(f, arg)
            self.assertFalse(future.done())
            self.assertTrue(future.cancel())
            self.assertTrue(future.cancelled())
            with self.assertRaises(pyfora.CancelledError):
                future.result()


    def test_divide_by_zero(self):
        with self.create_executor() as executor:
            def f(x):
                return 1/x
            arg = 0

            future = executor.submit(f, arg)
            with self.assertRaises(pyfora.PyforaError):
                future.result().toLocal().result()

    def test_convertListOfTuple(self):
        x = [(3,4)]

        def returnX():
            return x

        self.equivalentEvaluationTest(returnX)

    def test_boolean_conversion(self):
        class HasBoolConversion:
            def __init__(self, x):
                self.x = x

            def __nonzero__(self):
                return bool(self.x)

        class HasNoBoolConversion:
            pass

        candidates = [
            0, 1, 
            0.0, 1.0, 
            "", "string", 
            False, True, 
            lambda x:x,
            HasBoolConversion(0),
            HasBoolConversion(1),
            HasNoBoolConversion(),
            None,
            (), (1,), (3,4),
            [], [1], [1,2],
            {}, {1:2}, {1:2, 3:4},
            bool, type(None)
            ]

        self.equivalentEvaluationTest(lambda : [bool(c) for c in candidates])
        self.equivalentEvaluationTest(lambda : [True if c else False for c in candidates])

    def test_operator_pos_neg_invert(self):
        class HasPos:
            def __pos__(self):
                return 1

        class HasNeg:
            def __neg__(self):
                return 1

        class HasInvert:
            def __invert__(self):
                return 1

        class HasNothing:
            pass

        candidates = [
            0, 1, -1,
            0.0, 1.0, 
            "string", 
            False, True, 
            lambda x:x,
            HasPos(),
            HasNeg(),
            HasInvert(),
            HasNothing(),
            None, (), [], {}, bool
            ]

        for c in candidates:
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: +x, c)
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: -x, c)
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: ~x, c)

    def test_builtins_any(self):
        self.equivalentEvaluationTest(any, [])
        self.equivalentEvaluationTest(any, [True])
        self.equivalentEvaluationTest(any, [True, False])
        self.equivalentEvaluationTest(any, [False, False])

    def test_builtins_all(self):
        self.equivalentEvaluationTest(all, [])
        self.equivalentEvaluationTest(all, [True])
        self.equivalentEvaluationTest(all, [True, False])
        self.equivalentEvaluationTest(all, [False, False])

    def test_reference_module(self):
        with self.create_executor() as executor:
            import socket
            def f():
                return str(socket)

            with self.assertRaises(pyfora.PythonToForaConversionError):
                executor.submit(f)

    def test_reference_nonexistent_module_member(self):
        with self.create_executor() as executor:
            import socket
            def f():
                return socket.this_doesnt_exist

            with self.assertRaises(pyfora.PythonToForaConversionError):
                executor.submit(f)


    def test_invalid_apply(self):
        with self.create_executor() as executor:
            def f(x):
                return x[0]
            arg = 0

            future = executor.submit(f, arg)
            with self.assertRaises(pyfora.ComputationError):
                try:
                    print "result=",future.result()
                    print future.result().toLocal().result()
                except Exception as e:
                    print e
                    raise

    def test_conversion_error(self):
        with self.create_executor() as executor:
            def f(x):
                y = [1, 2, 3, 4]
                y[1] = x
                return y

            future = executor.define(f)
            with self.assertRaises(pyfora.PythonToForaConversionError):
                future.result()

    def test_pass_returns_None(self):
        with self.create_executor() as executor:
            def f():
                pass

            self.assertIs(self.evaluateWithExecutor(f), None)

    def test_run_off_end_of_function_returns_None(self):
        with self.create_executor() as executor:
            def f():
                x = 10

            self.assertIs(self.evaluateWithExecutor(f), None)

    def test_run_off_end_of_class_member_function_returns_None(self):
        with self.create_executor() as executor:
            def f():
                class X2:
                    def f(self):
                        x = 10

                return X2().f()

            self.assertIs(self.evaluateWithExecutor(f), None)

    def test_class_member_function_return_correct(self):
        with self.create_executor() as executor:
            def f():
                class X2:
                    def f(self):
                        return 10

                return X2().f()

            self.assertIs(self.evaluateWithExecutor(f), 10)

    def test_run_off_end_of_class_member_function_returns_None_2(self):
        with self.create_executor() as executor:
            class X3:
                def f(self):
                    x = 10

            def f():
                return X3().f()

            self.assertIs(self.evaluateWithExecutor(f), None)

    def test_empty_return_returns_None(self):
        with self.create_executor() as executor:
            def f():
                return

            self.assertIs(self.evaluateWithExecutor(f), None)

    def test_negate_int(self):
        with self.create_executor() as executor:
            def f(): return -10
            self.equivalentEvaluationTest(f)

    def test_sum_xrange(self):
        with self.create_executor() as executor:
            arg = 1000000000
            def f():
                return sum(xrange(arg))

            self.assertEqual(self.evaluateWithExecutor(f), arg*(arg-1)/2)

    def test_xrange(self):
        with self.create_executor() as executor:
            low = 0
            for high in [None] + range(-7,7):
                for step in [-3,-2,-1,None,1,2,3]:
                    print low, high, step
                    if high is None:
                        self.equivalentEvaluationTest(range, low)
                    elif step is None:
                        self.equivalentEvaluationTest(range, low, high)
                    else:
                        self.equivalentEvaluationTest(range, low, high, step)


    def test_jsonConversionError(self):
        with self.create_executor(allowCached=False) as executor:
            def f():
                pass

            errorMsg = "I always throw!"

            class MyException(Exception):
                pass

            def alwaysThrows(*args):
                raise MyException(errorMsg)

            # to make our a toLocal call throw an expected exception
            executor.objectRehydrator.convertJsonResultToPythonObject = alwaysThrows

            func_proxy = executor.define(f).result()
            res_proxy = func_proxy().result()

            try:
                res_proxy.toLocal().result()
            except Exception as e:
                self.assertIsInstance(e, pyfora.PyforaError)
                self.assertIsInstance(e.message, MyException)
                self.assertEqual(e.message.message, errorMsg)

    def test_iterable_is_pyfora_object(self):
        def it(x):
            while x > 0:
                yield x
                x = x - 1

        def f():
            return it(10).__is_pyfora__

        self.assertIs(self.evaluateWithExecutor(f), True)

    def test_free_function_is_pyfora_object(self):
        def g():
            return 10
        def f():
            return g.__is_pyfora__

        self.assertIs(self.evaluateWithExecutor(f), True)

    def test_local_function_is_pyfora_object(self):
        def f():
            def g():
                pass
            return g.__is_pyfora__

        self.assertIs(self.evaluateWithExecutor(f), True)

    def test_list_on_iterable(self):
        def it(x):
            while x > 0:
                yield x
                x = x - 1

        def f1():
            return list(xrange(10))

        def f2():
            return list(it(10))

        self.equivalentEvaluationTest(f1)
        self.equivalentEvaluationTest(f2)

    def test_member_access(self):
        def g():
            return 10
        def f():
            return g().__str__()

        self.equivalentEvaluationTest(f)

    def test_convert_lambda_external(self):
        g = lambda: 10
        def f():
            return g()

        self.equivalentEvaluationTest(f)

    def test_convert_lambda_internal(self):
        def f():
            g = lambda: 10
            return g()

        self.equivalentEvaluationTest(f)

    def test_evaluate_lambda_directly(self):
        self.equivalentEvaluationTest(lambda x,y: x+y, 10, 20)

    def test_return_lambda(self):
        def f():
            return lambda: 10

        self.assertEqual(self.evaluateWithExecutor(f)(), 10)

    def test_GeneratorExp_works(self):
        self.equivalentEvaluationTest(lambda: list(x for x in xrange(10)))

    def test_is_returns_true(self):
        self.equivalentEvaluationTest(lambda x: x is 10, 10)
        self.equivalentEvaluationTest(lambda x: x is 10, 11)

    def test_sum_on_generator(self):
        class Generator1:
            def __pyfora_generator__(self):
                return self

            def __init__(self, x, y, func):
                self.x = x
                self.y = y
                self.func = func

            def __iter__(self):
                yield self.func(self.x)

            def isNestedGenerator(self):
                return False

            def canSplit(self):
                return self.x + 1 < self.y

            def split(self):
                if not self.canSplit():
                    return None

                return (
                    Generator1(self.x, (self.x+self.y)/2, self.func),
                    Generator1((self.x+self.y)/2, self.y, self.func)
                    )

            def map(self, mapFun):
                newMapFun = lambda x: mapFun(self.func(x))
                return Generator1(self.x, self.y, newMapFun)

        def f():
            return sum(Generator1(0, 100, lambda x:x))

        self.assertEqual(f(), 0)
        self.assertEqual(self.evaluateWithExecutor(f), sum(xrange(100)))

    def test_tuples_are_pyfora_objects(self):
        def f():
            return (1,2,3).__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_generators_splittable(self):
        def f():
            return [1,2,3].__pyfora_generator__().canSplit()

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_generators_splittable(self):
        def f():
            return [1,2,3].__pyfora_generator__().canSplit()

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_generators_mappable(self):
        def f():
            return list([1,2,3].__pyfora_generator__().map(lambda z:z*2)) == [2,4,6]

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_split_xrange(self):
        def f():
            g = xrange(100).__pyfora_generator__().split()[0]
            res = []
            for x in g:
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_split_mapped_xrange(self):
        def f():
            g = xrange(100).__pyfora_generator__().map(lambda x:x).split()[0]
            res = []
            for x in g:
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_map_split_xrange(self):
        for ix in range(10):
            def f():
                g = xrange(100).__pyfora_generator__().split()[0].map(lambda x:x)
                res = []
                for x in g:
                    res = res + [x]

                return res == range(50)

            self.assertTrue(self.evaluateWithExecutor(f))


    def test_iterate_xrange(self):
        def f():
            res = []

            for x in xrange(50):
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_xrange_generator(self):
        def f():
            res = []

            for x in xrange(50).__pyfora_generator__().map(lambda x:x):
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_xrange_empty(self):
        def f():
            res = []

            for x in xrange(0):
                res = res + [x]

            return res == []

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_on_xrange(self):
        for ct in [0,1,2,4,8,16,32,64,100,101,102,103]:
            self.equivalentEvaluationTest(lambda: sum(x for x in xrange(ct)))
            self.equivalentEvaluationTest(lambda: list(x for x in xrange(ct)))
            self.equivalentEvaluationTest(lambda: [x for x in xrange(ct)])

    def test_filtered_generator_expression(self):
        for ct in [0,1,2,4,8,16,32,64,100,101,102,103]:
            self.equivalentEvaluationTest(lambda: sum(x for x in xrange(ct) if x < ct / 2))
            self.equivalentEvaluationTest(lambda: list(x for x in xrange(ct) if x < ct / 2))
            self.equivalentEvaluationTest(lambda: [x for x in xrange(ct) if x < ct / 2])

    def test_filtered_nested_expression(self):
        for ct in [0, 1, 2, 4, 8, 16, 32, 64]:
            self.equivalentEvaluationTest(lambda: sum((outer * 503 + inner for outer in xrange(ct) for inner in xrange(outer))))
            self.equivalentEvaluationTest(lambda: sum((outer * 503 + inner for outer in xrange(ct) if outer % 2 == 0 for inner in xrange(outer))))
            self.equivalentEvaluationTest(lambda: sum((outer * 503 + inner for outer in xrange(ct) if outer % 2 == 0 for inner in xrange(outer) if inner % 2 == 0)))
            self.equivalentEvaluationTest(lambda: sum((outer * 503 + inner for outer in xrange(ct) for inner in xrange(outer) if inner % 2 == 0)))
        
    def test_types_and_combos(self):
        types = [bool, str, int, type, object, list, tuple, dict]
        instances = [10, "10", 10.0, None, True, [], (), {}] + types
        callables = types + [lambda x: x.__class__]

        for c in callables:
            for i in instances:
                self.equivalentEvaluationTestThatHandlesExceptions(c, i)

    def test_issubclass(self):
        test = self.equivalentEvaluationTestThatHandlesExceptions
        types = [float, int, bool, object, Exception]

        for t1 in types:
            for t2 in types:
                test(issubclass, t1, t2)
                test(issubclass, t1, (t2,))

    def test_isinstance(self):
        test = self.equivalentEvaluationTestThatHandlesExceptions

        for inst in [10, 10.0, True]:
            for typ in [float, object, int, bool]:
                test(lambda: isinstance(inst, typ))
                test(lambda: issubclass(type(inst), typ))

        
    def test_sum_isPrime(self):
        def isPrime(p):
            x = 2
            while x*x <= p:
                if p%x == 0:
                    return 0
                x = x + 1
            return x

        self.equivalentEvaluationTest(lambda: sum(isPrime(x) for x in xrange(1000000)))

    def test_inStatement_1(self):
        def f():
            x = [0,1,2,3]
            return 0 in x

        self.equivalentEvaluationTest(f)

    def test_iteration_1(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.equivalentEvaluationTest(iteration_1)

    def test_nestedComprehensions_1(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.equivalentEvaluationTest(nestedComprehensions)

    def test_listComprehensions_1(self):
        def listComprehensions_1():
            aList = [0,1,2,3]
            aList = [elt * 2 for elt in aList]
            return aList[-1]

        self.equivalentEvaluationTest(listComprehensions_1)

    def test_listComprehensions_2(self):
        def listComprehensions_2(arg):
            aList = range(4)
            filteredList = [elt for elt in aList if elt % 2 == 0]
            return filteredList[arg]

        for ix in range(-2, 2):
            self.equivalentEvaluationTest(listComprehensions_2, ix)

    def test_listComprehensions_3(self):
        def listComprehensions_3():
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[1][0]

        self.equivalentEvaluationTest(listComprehensions_3)

    def test_listComprehensions_4(self):
        def listComprehensions_4(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]
            return aList[arg]

        for ix in range(-7, 7):
            self.equivalentEvaluationTest(listComprehensions_4, ix)

    def test_basicLists_1(self):
        def basicLists(x):
            aList = [x] + [x]
            return aList[0] + aList[1]

        self.equivalentEvaluationTest(basicLists, 1)

    def test_pyTuples_1(self):
        def f(ix):
            t = (1,2,3)
            return t[ix]

        for ix in range(-3,3):
            self.equivalentEvaluationTest(f, ix)

    def test_pyTuples_3(self):
        def f(elt):
            t = (1,2,3)
            return t.index(elt)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)

    def test_ints(self):
        def f():
            x = 100
            return x

        self.equivalentEvaluationTest(f)

    def test_ints_1(self):
        def f():
            return 42

        self.equivalentEvaluationTest(f)

    def test_ints_2(self):
        def f():
            return 2 == 2

        self.equivalentEvaluationTest(f)

    def test_floats_1(self):
        def f():
            return 42.0

        self.equivalentEvaluationTest(f)

    def test_bools_1(self):
        def f():
            return True

        self.equivalentEvaluationTest(f)

    def test_strings_1(self):
        def f():
            x = "asdf"
            return x

        self.equivalentEvaluationTest(f)

    def test_len_1(self):
        class ThingWithLen:
            def __init__(self, len):
                self.len = len
            def __len__(self):
                return self.len

        def f(x):
            return len(ThingWithLen(x))

        self.equivalentEvaluationTest(f, 2)

    def test_len_2(self):
        def f():
            return len([1,2,3])

        self.equivalentEvaluationTest(f)

    def test_len_3(self):
        def f():
            return len("asdf")

        self.equivalentEvaluationTest(f)

    def test_str_1(self):
        class ThingWithStr:
            def __init__(self, str):
                self.str = str
            def __str__(self):
                return self.str

        def f(x):
            return str(ThingWithStr(x))

        self.equivalentEvaluationTest(f, "2")

    def test_str_2(self):
        def f(x):
            return str(x)
            
        self.equivalentEvaluationTest(f, 42)
        self.equivalentEvaluationTest(f, "foo")
        self.equivalentEvaluationTest(f, None)

    def test_functions_1(self):
        def f(x):
            return x + 1

        for ix in range(3):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_2(self):
        y = 3
        def f(x):
            return x + y

        for ix in range(3):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_4(self):
        def f(x):
            if x < 0:
                return x
            return x + g(x - 1)
        def g(x):
            if x < 0:
                return x
            return x * f(x - 1)

        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_mutual_recursion_across_modules(self):
        import ufora.FORA.python.PurePython.testModules.MutualRecursionAcrossModules.A as A


        for ix in range(4):
            self.equivalentEvaluationTest(A.f, ix)

    def test_functions_5(self):
        def f(x):
            def g():
                return 1 + x
            return g()

        for ix in range(-3,0):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_7(self):
        w = 3
        def h(x):
            return w + 2 * x
        def f(x):
            if x < 0:
                return x
            return g(x - 1) + h(x)
        def g(x):
            if x < 0:
                return x
            return f(x - 1) + h(x - 1)

        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_8(self):
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

        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_functions_9(self):
        y = 2
        def h(x, fn):
            if x < 0:
                return x
            return x + y * fn(x - 1)
        def f(x):
            def g(arg):
                if arg < 0:
                    return x + arg
                return x * h(arg - 1, g)
            return g

        for ix in range(10):
            self.equivalentEvaluationTest(f(2), ix)

    def test_functions_10(self):
        y = 3
        def f(x):
            if x <= 0:
                return x
            return x + g(x - 1)
        def g(x):
            if x <= 0:
                return x
            return y + f(x - 2) + h(x - 3)
        def h(x):
            return x + 1

        arg = 10
        self.equivalentEvaluationTest(f, arg)
        self.equivalentEvaluationTest(g, arg)
        self.equivalentEvaluationTest(h, arg)
        
    def test_classes_1(self):
        class C1:
            def __init__(self, x):
                self.x = x
            def f(self, arg):
                return self.x + arg

        def f(x):
            c = C1(x)
            return c.f(x)

        self.equivalentEvaluationTest(f, 10)

    def test_classes_2(self):
        a = 2
        def func_1(arg):
            return arg + a
        class C2:
            def __init__(self, x):
                self.x = x
            def func_2(self, arg):
                return self.x + func_1(arg)

        def f(x, y):
            c = C2(x)
            return c.func_2(y)

        self.equivalentEvaluationTest(f, 2, 3)

    def test_classes_3(self):
        class C3:
            @staticmethod
            def g(x):
                return x + 1

        def f(x):
            return C3.g(x)

        self.equivalentEvaluationTest(f, 2)

    def test_class_instances_1(self):
        class C4:
            def __init__(self, x, y):
                self.x = x
                self.y = y
                self.z = x + y
            def f(self, arg):
                return arg + self.x + self.y + self.z

        c = C4(100, 200)

        def f(arg):
            return c.f(arg)

        self.equivalentEvaluationTest(f, 4)
        
        def members():
            return (c.x, c.y, c.z)

        self.equivalentEvaluationTest(members)

    def test_class_instances_2(self):
        class C5:
            def __init__(self, x):
                self.x = x
            def f(self, y):
                return self.x + y

        c = C5(42)

        def f(arg):
            return c.f(arg)

        def g():
            return c.x

        self.equivalentEvaluationTest(f, 10)
        self.equivalentEvaluationTest(g)

    def test_class_instances_3(self):
        class C6:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        c = C6(1, 2)

        def f():
            return (c.x, c.y)

    def test_class_instances_5(self):
        class C8:
            def __init__(self, x):
                self.x = x

            def f(self, arg):
                if arg <= 0:
                    return self.x
                return arg * self.g(arg - 1)

            def g(self, arg):
                if arg <= 0:
                    return (-1) * self.x
                return arg + self.f(arg - 2)

        c = C8(10)

        def f():
            return c.x

        self.equivalentEvaluationTest(f)

        def g(arg):
            return c.f(arg)

        for arg in range(10):
            self.equivalentEvaluationTest(g, arg)

    def test_freeVariablesInClasses_1(self):
        x = 42
        class C11:
            @staticmethod
            def f1(x):
                return x
            @staticmethod
            def f2(arg):
                return x + arg
            def f3(self, arg):
                return x + arg
            def f4(self, x):
                return x

        def f(arg):
            return (C11.f1(arg), C11.f2(arg))

        self.equivalentEvaluationTest(f, 0)
        self.equivalentEvaluationTest(f, 1)

        c = C11()

        def g(arg):
            return (c.f3(arg), c.f4(arg))

        self.equivalentEvaluationTest(g, 0)
        self.equivalentEvaluationTest(g, 1)

    def test_freeVariablesInClasses_2(self):
        class C12:
            def __init__(self, x):
                self.x = x

        c8 = C12(42)
        class C13:
            def f(self, arg):
                if arg < 0:
                    return 0
                return c8.x + self.g(arg - 1)
            def g(self, arg):
                if arg < 0:
                    return arg
                return c8.x * self.f(arg - 2)

        c = C13()

        def f(arg):
            return c.f(arg), c.g(arg)

        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_freeVariablesInClasses_4(self):
        class C_freeVars_4_1:
            @staticmethod
            def f(x):
                return x + 1

        class C_freeVars_4_2:
            def g(self, arg):
                if arg < 0:
                    return 0
                return C_freeVars_4_1.f(arg) + self.h(arg - 1)
            def h(self, arg):
                if arg < 0:
                    return arg
                return C_freeVars_4_1.f(arg) * self.g(arg - 2)

        c = C_freeVars_4_2()

        def f(arg):
            return c.h(arg), c.g(arg)

        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_freeVariablesInClasses_5(self):
        class C_freeVars_5_1:
            def f(self, x):
                return x + 1

        c = C_freeVars_5_1()
        class C_freeVars_5_2:
            def f(self, arg):
                if arg < 0:
                    return 0
                return c.f(arg) + self.g(arg - 1)
            def g(self, arg):
                if arg < 0:
                    return arg
                return c.f(arg) * self.f(arg - 2)

        c2 = C_freeVars_5_2()

        def f(arg):
            return c2.f(arg), c2.g(arg)
        
        for ix in range(10):
            self.equivalentEvaluationTest(f, ix)

    def test_freeVariablesInClasses_6(self):
        x = 2
        class C_freeVars_6_1:
            def f(self):
                return x

        c = C_freeVars_6_1()

        def f():
            return c.f()

        self.equivalentEvaluationTest(f)

    def test_freeVariablesInClasses_7(self):
        class C_freeVars_7_1:
            def f(self, arg):
                return arg + 1

        c = C_freeVars_7_1()
        def f(x):
            return c.f(x)

        self.equivalentEvaluationTest(f, 10)

    def test_lists_1(self):
        x = [1,2,3,4]

        def f(ix):
            return x[ix]

        for ix in range(-len(x), len(x)):
            self.equivalentEvaluationTest(f, ix)

    def test_lists_2(self):
        class C_lists:
            def __init__(self, x):
                self.x = x
            def __eq__(self, other):
                return self.x == other.x

        xs = [1,2,3,C_lists(3)]

        def elt(ix):
            return xs[ix]

        for ix in range(-4,4):
            self.equivalentEvaluationTest(elt, ix)

    def test_classes_with_getitems(self):
        class C_with_getitem:
            def __init__(self, m):
                self.__m__ = m

            def __getitem__(self, ix):
                return self.__m__[ix]

        size = 10
        c = C_with_getitem(range(10))

        def f(ix):
            return c[ix]
        
        for ix in range(size):
            self.equivalentEvaluationTest(f, ix)

    def test_lists_with_circular_references_1(self):
        circularList = [1,2,3]
        circularList.append(circularList)

        def f():
            return circularList

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_lists_with_circular_references_2(self):
        circularList = [1,2,3]
        class SomeClass1:
            def __init__(self, val):
                self.__m__ = val
        circularList.append(SomeClass1(circularList))

        def f():
            return circularList

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_lists_with_circular_references_3(self):
        circularList = [1,2,3]
        class SomeClass2:
            def __init__(self, val):
                self.__m__ = val
        circularList.append(
            SomeClass2(
                SomeClass2(
                    [circularList, 2]
                    )
                )
            )

        def f():
            return circularList

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_dicts(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f(key):
            return x[key]

        for key in x:
            self.equivalentEvaluationTest(f, key)
        
    def test_implicitReturnNone_1(self):
        def f():
            x = 2

        self.equivalentEvaluationTest(f)

    def test_implicitReturnNone_2(self):
        def f(x):
            x

        self.equivalentEvaluationTest(f, 2)

    def test_implicitReturnNone_3(self):
        def f(x):
            if x > 0:
                return
            else:
                return 1

        self.equivalentEvaluationTest(f, 1)
        self.equivalentEvaluationTest(f, -1)

    def test_loopsum(self):
        def loopSum(x):
            y = 0
            while x > 0:
                y = y + x
                x = x - 1
            return y

        for ix in range(3):
            self.equivalentEvaluationTest(loopSum, ix)


    def test_inlineFunction(self):
        def inlineFunction(x):
            def z(y):
                return x+y
            return z(10)

        for ix in range(4):
            self.equivalentEvaluationTest(inlineFunction, ix)

    def test_lambdaFunction(self):
        def lambdaFunction(x):
            z = lambda y: x + y
            return z(10)

        for ix in range(4):
            self.equivalentEvaluationTest(lambdaFunction, ix)

    def test_isPrime(self):
        def isPrime(p):
            x = 2
            while x * x <= p:
                if p % x == 0:
                    return 0
                x = x + 1
            return 0

        for ix in range(10):
            self.equivalentEvaluationTest(isPrime, ix)

    def test_whileLoop(self):
        def whileLoop(x):
            y = 0
            while x < 100:
                y = y + x
                x = x + 1
            return y

        for ix in range(4):
            self.equivalentEvaluationTest(whileLoop, ix)

    def test_variableAssignment(self):
        def variableAssignment(x):
            y = x + 1
            return x+y

        for ix in range(3):
            self.equivalentEvaluationTest(variableAssignment, ix)


    def test_argumentAssignment(self):
        def argumentAssignment(x):
            x = x + 1
            return x

        self.equivalentEvaluationTest(argumentAssignment, 100)

    def test_basicAddition(self):
        def basicAddition(x):
            return x + 1

        self.equivalentEvaluationTest(basicAddition, 4)

    def test_listComprehensions_5(self):
        def listComprehensions_3(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[arg]

        for ix in range(-9,9):
            self.equivalentEvaluationTest(listComprehensions_3, ix)

    def test_listComprehensions_6(self):
        def listComprehensions_1(arg):
            aList = [0,1,2,3]
            aList = [elt * 2 for elt in aList]
            return aList[arg]

        for ix in range(-4, 4):
            self.equivalentEvaluationTest(listComprehensions_1, ix)

    def test_nestedComprehensions_2(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.equivalentEvaluationTest(nestedComprehensions)

    def test_returningTuples_1(self):
        def returningATuple_1():
            return (0, 1)

        self.equivalentEvaluationTest(returningATuple_1)

    def test_returningTuples_2(self):
        def returningATuple_2():
            return 0, 1

        self.equivalentEvaluationTest(returningATuple_2)

    def test_pass(self):
        def passStatement():
            def f():
                pass

            x = f()
            return x

        self.equivalentEvaluationTest(passStatement)

    def test_iteration_2(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.equivalentEvaluationTest(iteration_1)

    def test_inStatement_2(self):
        def inStatement():
            x = [0,1,2,3]
            return 0 in x

        self.equivalentEvaluationTest(inStatement)

    def test_nestedLists_1(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.equivalentEvaluationTest(nestedLists)

    def test_recursiveFunctions_1(self):
        def fact(n):
            if n == 0:
                return 1
            return n * fact(n - 1)

        for ix in range(5):
            self.equivalentEvaluationTest(fact, ix)

    def test_recursiveFunctions_2(self):
        def fib(n):
            if n <= 1:
                return n

            return fib(n - 1) + fib(n - 2)

        for ix in range(5):
            self.equivalentEvaluationTest(fib, ix)

    def test_initMethods_1(self):
        class A1():
            def __init__(self):
                class B():
                    pass                

        def f():
            a = A1()
            return None

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_initMethods_2(self):
        class A2():
            def __init__(self):
                def foo():
                    pass

        def f():
            a = A2()
            return None

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_initMethods_3(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x + arg
            return A(2).x

        for ix in range(-10, 10):
            self.equivalentEvaluationTest(f, ix)

    def test_initMethods_4(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self_x = arg
                    self.x = x + self_x
            return A(2).x

        for ix in range(4):
            self.equivalentEvaluationTest(f, ix)

    def test_initMethods_5(self):
        def f():
            class A():
                def __init__(self, x):
                    self = 2
                    self.x = x
            return None

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_initMethods_6(self):
        def f():
            class A():
                def __init__(self, x):
                    (self.x, self.y) = (x, x + 1)
            return A(2).x

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_initMethods_7(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x
                    self.y = self.x + 1
            return A(arg).x

        for ix in range(3):
            self.equivalentEvaluationTest(f, ix)

    def test_initMethods_8(self):
        def f(arg):
            class A():
                def __init__(selfArg):
                    selfArg.x = 2
                    selfArg.x = selfArg.x + 1
            return A().x + arg

        for ix in range(4):
            self.equivalentEvaluationTest(f, ix)

    def test_initMethods_9(self):
        def f(arg):
            class A():
                def __init__(self, x):
                    self.x = x
                    self.x = self.x + 1
                def foo(self, y):
                    return self.x + y

            return A(arg).foo(2)

        for ix in range(4):
            self.equivalentEvaluationTest(f, ix)

    def test_initMethods_10(self):
        def f(_):
            class A():
                def __init__(selfArg, x):
                    if x > 0:
                        selfArg.x = x
                    else:
                        selfArg.x = (-1) * x

            return A(1).x + A(-1).x

        for ix in range(-4,1):
            self.equivalentEvaluationTest(f, ix)

    def test_functionsWithTheSameName(self):
        # inspect, from the python std library, which we use,
        # does the right thing for functions.
        # the corresponding test for classes fails
        def f1():
            def f():
                return 1
            return f
        def f2():
            def f():
                return -1
            return f

        self.equivalentEvaluationTest(f1())
        self.equivalentEvaluationTest(f2())

    def test_imports_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithImport \
            as ModuleWithImport

        self.equivalentEvaluationTest(ModuleWithImport.h, 2)

    def test_imports_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithOneMember \
            as ModuleWithOneMember

        def f(x):
            return ModuleWithOneMember.h(x)

        self.equivalentEvaluationTest(f, 2)

    def test_imports_3(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithUnconvertableMember \
            as ModuleWithUnconvertableMember

        def f(x):
            return ModuleWithUnconvertableMember.convertableMember(x)

        def unconvertable(x):
            return ModuleWithUnconvertableMember.unconvertableMember(x)

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(unconvertable, 2)

        self.equivalentEvaluationTest(f, 2)

    def test_closures_1(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures1 \
            as ModuleWithClosures1

        self.equivalentEvaluationTest(ModuleWithClosures1.f1, 3, 4)

    def test_closures_2(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithClosures2 \
            as ModuleWithClosures2

        self.equivalentEvaluationTest(ModuleWithClosures2.f2(3), 4)

    def test_mutuallyRecursiveModuleMembers_1(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers1 \
            as MutuallyRecursiveModuleMembers1

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers1.f, 2)

    def test_mutuallyRecursiveModuleMembers_2(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers2 \
            as MutuallyRecursiveModuleMembers2

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers2.f4, 109)

    def test_mutuallyRecursiveModuleMembers_3(self):
        import ufora.FORA.python.PurePython.testModules.MutuallyRecursiveModuleMembers3 \
            as MutuallyRecursiveModuleMembers1

        self.equivalentEvaluationTest(MutuallyRecursiveModuleMembers1.f, 5)

    def test_continue_in_while(self):
        def f():
            x = 0
            y = 0
            while x < 100:
                x = x + 1
                if x % 2:
                    continue
                y = y + x

        self.equivalentEvaluationTest(f)

    def test_continue_in_for(self):
        def f():
            x = 0
            y = 0
            for x in xrange(100):
                if x % 2:
                    continue
                y = y + x

        self.equivalentEvaluationTest(f)

    def test_setitem_exception_is_meaningful(self):
        def f():
            l = [1,2,3]
            l[0] = 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertTrue(e.trace is not None)
