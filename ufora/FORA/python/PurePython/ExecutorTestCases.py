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
import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora.Exceptions as Exceptions


import numpy
import time


class ExecutorTestCases(object):
    """ExecutorTestCases - mixin to define test cases for the pyfora Executor cass."""

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

    def resolvedFutures(self, futures):
        results = [f.result() for f in futures]
        localResults = [r.toLocal() for r in results]
        foraResults = []
        for f in localResults:
            try:
                foraResults.append(f.result())
            except:
                pass
        return foraResults

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

    def test_large_strings(self):
        def f():
            a = "val1"

            while len(a) < 1000000:
                a = a + a

            return a

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
        self.equivalentEvaluationTest(f)

    def test_len_on_tuple(self):
        def f():
            a = (9,)
            b = ()
            c = (1,2,4)
            return (len(a), len(b), len(c))

        self.evaluateWithExecutor(f)

    def test_return_list(self):
        def f():
            return [1, 2, 3, 4, 5]

        self.equivalentEvaluationTest(f)

    def test_tuple_eq_ne_1(self):
        t1 = (2,2)
        t2 = (1,4)
        
        self.equivalentEvaluationTest(
            lambda: (t1 == t2, t1 != t2)
            )

    def test_tuple_eq_ne_2(self):
        t1 = (2,2)
        t2 = t1
        
        self.equivalentEvaluationTest(
            lambda: (t1 == t2, t1 != t2)
            )

    def test_tuple_str(self):
        t1 = (2,2)
        self.equivalentEvaluationTest(
            lambda: str(t1)
            )

    def test_list_str(self):
        t1 = (2,2)
        self.equivalentEvaluationTest(
            lambda: str(t1)
            )

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
        self.assertEqual(res, ct * (ct-1) / 2)

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

    def test_len_0(self):
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
        self.assertIs(str, res)

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

    def test_methods_are_pyfora(self):
        class StaticMethodIsPyfora:
            @staticmethod
            def f(x):
                return x+1

            def g(self):
                return None

        self.assertTrue(self.evaluateWithExecutor(lambda: StaticMethodIsPyfora().g.__is_pyfora__))

        self.assertTrue(self.evaluateWithExecutor(lambda: StaticMethodIsPyfora().f.__is_pyfora__))

        self.assertTrue(self.evaluateWithExecutor(lambda: StaticMethodIsPyfora.f.__is_pyfora__))


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
        self.assertEqual(
            PyAstUtil.getSourceText(shouldBeToReturn), PyAstUtil.getSourceText(toReturn)
            )

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

    def test_is_returns_true(self):
        self.equivalentEvaluationTest(lambda x: x is 10, 10)
        self.equivalentEvaluationTest(lambda x: x is 10, 11)

    def test_tuples_are_pyfora_objects(self):
        def f():
            return (1,2,3).__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(f))

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

    def test_self_recursive_class_instance(self):
        class ClassThatRefersToOwnInstance:
            def f(self):
                return c
            def g(self):
                return 10

        c = ClassThatRefersToOwnInstance()

        with self.create_executor() as fora:
            try:
                fora.submit(lambda: c.f().g())
                self.assertFalse(True, "should have thrown")
            except Exceptions.PythonToForaConversionError as e:
                self.assertTrue("cannot be mutually recursive" in e.message, e.message)
                self.assertTrue(e.trace is not None)

    def test_lists_plus_nonlists(self):
        def f():
            try:
                return [] + 10
            except TypeError:
                return None

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_class_member_functions_are_pyfora_objects_1(self):
        class ClassMemberFunctionsArePyfora1:
            def f(self):
                return 10

        def f():
            return ClassMemberFunctionsArePyfora1().f.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_class_member_functions_are_pyfora_objects_2(self):
        def f():
            class ClassMemberFunctionsArePyfora2:
                def f(self):
                    return 10

            return ClassMemberFunctionsArePyfora2().f.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(f))


    def test_class_member_functions_nonstandard_self(self):
        def f():
            self = "outerSelf"
            class ClassMemberFunctionsNonstandardSelf:
                def f(notSelf):
                    return (notSelf.g(), self)

                def g(self):
                    return 'g'

            return ClassMemberFunctionsNonstandardSelf().f()

        self.assertTrue(self.evaluateWithExecutor(f))

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

    def test_dicts(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f(key):
            return x[key]

        for key in x:
            self.equivalentEvaluationTest(f, key)

    def test_dict_keys(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        self.equivalentEvaluationTest(
            lambda: x.keys(),
            comparisonFunction=lambda x, y: set(x) == set(y)
            )

    def test_dict_values(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        self.equivalentEvaluationTest(
            lambda: x.values(),
            comparisonFunction=lambda x, y: set(x) == set(y)
            )

    def test_dict_creation_1(self):
        x = [(1,2), (3,4)]

        def f():
            return dict(x)

        self.equivalentEvaluationTest(
            f,
            comparisonFunction=lambda x, y: x == y
            )

    def test_dict_creation_2(self):
        def f():
            return { x: x**2 for x in range(10) if x % 2 != 0 }

        self.equivalentEvaluationTest(
            f,
            comparisonFunction=lambda x, y: x == y
            )

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

    def test_initMethods_6(self):
        def f():
            class A():
                def __init__(self, x):
                    (self.x, self.y) = (x, x + 1)
            return A(2).x

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

    def test_import_example(self):
        import ufora.FORA.python.PurePython.testModules.import_example.B as B

        self.equivalentEvaluationTest(lambda: B.f(2))

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

    def test_list_containing_itself(self):
        evilList = []
        evilList.append(evilList)

        try:
            self.equivalentEvaluationTest(lambda: len(evilList))
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertEqual(
                e.message,
                "don't know how to convert lists or tuples which reference themselves"
                )

    def test_print(self):
        def f():
            print "hello world"

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertIn(
                "Pyfora can't convert this code",
                e.message
                )

    def test_docstrings_convert(self):
        def f1():
            class c:
                """docstring"""
                def m(self):
                    return 1

            return c().m()

        self.evaluateWithExecutor(f1)

        def f2():
            class c:
                def m(self):
                    """docstring"""
                    return 1

            return c().m()

        self.evaluateWithExecutor(f2)

    def test_import(self):
        def f():
            import sys

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertIn(
                "Pyfora can't convert this code",
                e.message
                )

    def test_uninitializedVars_1(self):
        def f():
            x = x
            return 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.ComputationError as e:
            self.assertIsInstance(e.remoteException, UnboundLocalError)

    def test_uninitializedVars_2(self):
        x = 2
        def f():
            x = x
            return 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.ComputationError as e:
            self.assertIsInstance(e.remoteException, UnboundLocalError)

    def test_uninitializedVars_3(self):
        x = 2
        def f(x):
            x = x
            return 0

        self.equivalentEvaluationTest(f, 2)

    def test_isinstance_class(self):
        class IsinstanceClassTest:
            pass

        def f():
            x = IsinstanceClassTest()
            return x.__class__ is IsinstanceClassTest and isinstance(x, IsinstanceClassTest)

        self.equivalentEvaluationTest(f)

    def test_tuple_assignment(self):
        def f():
            x,y = 1,2
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_larger(self):
        def f():
            x,y = 1,2,3
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_smaller(self):
        def f():
            x,y,z = 1,2
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield(self):
        def f():
            def it():
                yield 1
                yield 2
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield_larger(self):
        def f():
            def it():
                yield 1
                yield 2
                yield 3
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield_smaller(self):
        def f():
            def it():
                yield 1
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_nested(self):
        def f():
            x,(y,z) = (1,(2,3))
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_nested_2(self):
        def f():
            x,(y,z) = (1,[2,3])
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_unpack_in_loop(self):
        def func():
            f = lambda x: x+1
            g = lambda x: x+2
            res = 0
            for ct in xrange(1000000000):
                res = res + f(ct)
                f,g = g,f
            return res

        #this should take forever if compilation of tuple assignment
        #is not working correctly
        self.evaluateWithExecutor(func)

    def test_custom_slicing_1(self):
        class ListWrapper_1:
            def __init__(self, m):
                self.m = m
            def __getitem__(self, maybeSlice):
                if isinstance(maybeSlice, slice):
                    return self.m[maybeSlice]
                return -100000

        def f():
            l = ListWrapper_1(range(10))
            return (l[1:4], l[:3], l[:], l[::], l[3:], l[4::2], l[4])

        self.equivalentEvaluationTest(f)

    def test_custom_slicing_2(self):
        class ListWrapper_2:
            def __init__(self, m):
                self.m = m
            def __getitem__(self, maybeSlice):
                if isinstance(maybeSlice, slice):
                    return self.m[maybeSlice]
                if isinstance(maybeSlice, tuple):
                    return [self.m[bla] for bla in maybeSlice]
                return -100000

        def f():
            l = ListWrapper_2(range(10))
            return l[:, 1:4, 3:9]

        self.equivalentEvaluationTest(f)

    def test_returning_slice_1(self):
        def f1():
            return slice

        self.equivalentEvaluationTest(f1)

    def test_inserting_slice_1(self):
        def f():
            s = slice(1,2,3)
            x = range(10)
            return x[s]

        self.equivalentEvaluationTest(f)

    def test_unbound_variable_access_throws(self):
        def f():
            x = 10
            try:
                if x is asdf:
                    return 10

                asdf = 100
            except UnboundLocalError:
                return True

        self.equivalentEvaluationTest(f)

    def test_unbound_variable_access_in_class_throws(self):
        class UnboundVariableAccessInClass:
            def f(self):
                x = 10
                try:
                    if x is asdf:
                        return 10

                    asdf = 100
                except UnboundLocalError:
                    return True

        self.equivalentEvaluationTest(lambda: UnboundVariableAccessInClass().f())

    def test_access_list_comprehension_variable_fails(self):
        def f():
            try:
                result = [x for x in range(10)]
                return x
            except Exception:
                return "Exception"

        try:
            result = self.evaluateWithExecutor(f)
            self.assertTrue(False, result)
        except Exceptions.ComputationError as e:
            self.assertIsInstance(e.remoteException, Exceptions.InvalidPyforaOperation)

    def test_convert_instance_method_from_server(self):
        def f(x):
            class InstanceMethodFromServer:
                def __init__(self, x):
                    self.x = x
                def f(self):
                    return self.x + 1

            return InstanceMethodFromServer(x).f

        self.assertEqual(self.evaluateWithExecutor(f, 1)(), 2)

    def test_convert_instance_method_from_client(self):
        class InstanceMethodFromClient:
            def __init__(self, x):
                self.x = x
            def f(self):
                return self.x + 1

        def f(x):
            return InstanceMethodFromClient(x).f

        self.assertEqual(self.evaluateWithExecutor(InstanceMethodFromClient(1).f), 2)

    def test_for_loop_values_carry_over(self):
        with self.create_executor() as executor:
            def f():
                y = 0
                for x in [1, 2, 3, 4]:
                    y = y + x

                return (y, x)

            self.equivalentEvaluationTest(f)

    def test_holding_a_mappable_1(self):
        x = [len]
        def f():
            return x

        self.equivalentEvaluationTest(f)
        
    def test_holding_a_mappable_2(self):
        y = numpy.array(range(5))
        x = [y]
        def f():
            return x[0]

        self.equivalentEvaluationTest(f)

    def test_static_method_on_instance(self):
        class StaticMethodInInstance:
            @staticmethod
            def f():
                return 10

        self.equivalentEvaluationTest(lambda: StaticMethodInInstance().f() is None)

    def test_static_method_run_off_end_is_none(self):
        class StaticMethodRunOffEndIsNone:
            @staticmethod
            def f():
                return 10

        self.equivalentEvaluationTest(lambda: StaticMethodRunOffEndIsNone.f() is None)

    def test_static_method_name_is_noncapturing(self):
        def f():
            return 11
        class StaticMethodNameNoncapturing:
            @staticmethod
            def f():
                return 10

        self.equivalentEvaluationTest(lambda: StaticMethodNameNoncapturing.f() is None)

    def test_mutual_recursion(self):
        def f(n):
            if n < 0:
                return n
            return g(n - 1)
        def g(n):
            if n < -1:
                return n
            return f(n - 2)

        self.equivalentEvaluationTest(f, 4)

    def test_empty_iterator(self):
        def sequence(ct):
            while ct > 0:
                yield ct
                ct = ct - 1

        class EmptyIterator:
            @staticmethod
            def staticSequence(ct):
                while ct > 0:
                    yield ct
                    ct = ct - 1

            def sequence(self, ct):
                while ct > 0:
                    yield ct
                    ct = ct - 1

        self.equivalentEvaluationTest(lambda: list(sequence(1)))

        for count in [0,1,2]:
            self.equivalentEvaluationTest(lambda: list(sequence(count)))
            self.equivalentEvaluationTest(lambda: list(EmptyIterator.staticSequence(count)))
            self.equivalentEvaluationTest(lambda: list(EmptyIterator().sequence(count)))

    def test_properties_1(self):
        class C_with_properties_1:
            def __init__(self, m):
                self.m = m
            def f(self, x):
                return self.m + x
            @property
            def prop(self):
                return self.f(self.m)

        def f():
            return C_with_properties_1(42).prop

        self.equivalentEvaluationTest(f)

    def test_range_perf(self):
        ct = 1000
        while ct < 10000000:
            t0 = time.time()
            x = self.evaluateWithExecutor(range, ct)
            print (time.time() - t0), ct, ct / (time.time() - t0), " per second."

            ct = ct * 2

    def test_complex(self):
        self.equivalentEvaluationTest(lambda: abs(complex(1.0,0.0) * complex(1.0,0.0)))
    
