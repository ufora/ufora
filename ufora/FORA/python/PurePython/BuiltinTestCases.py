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
import pyfora.Exceptions as Exceptions

import time


class BuiltinTestCases(object):
    def test_range_builtin_simple(self):
        def f(x):
            return range(x)

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

    def test_ord_chr_builtins(self):
        def f():
            chars = [chr(val) for val in range(40, 125)]
            vals = [ord(val) for val in chars]
            return (chars, vals)

        self.equivalentEvaluationTest(f)

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
        self.equivalentEvaluationTest(f, [False])
        self.equivalentEvaluationTest(f, [True, True])
        self.equivalentEvaluationTest(f, [True, False])
        self.equivalentEvaluationTest(f, [False, True])
        self.equivalentEvaluationTest(f, [False, False])

    def test_builtins_any(self):
        def f(x):
            return any(x)
        self.equivalentEvaluationTest(f, [])
        self.equivalentEvaluationTest(f, [True])
        self.equivalentEvaluationTest(f, [False])
        self.equivalentEvaluationTest(f, [True, True])
        self.equivalentEvaluationTest(f, [True, False])
        self.equivalentEvaluationTest(f, [False, True])
        self.equivalentEvaluationTest(f, [False, False])

    def test_builtins_zip_not_implemented(self):
        def f(x):
            return zip(x)

        with self.assertRaises(pyfora.Exceptions.PyforaNotImplementedError):
            self.equivalentEvaluationTest(f, [])

    def test_reversed_builtins(self):
        def f():
            a = [1, 2, 3, 4, 5, 6]
            b = reversed(a)
            toReturn = []
            for v in b:
                toReturn = toReturn + [v]
            return toReturn

        self.equivalentEvaluationTest(f)

    def test_reduce_builtin(self):
        def mul(x,y): return x*y
        def sub(x,y): return x-y
        self.equivalentEvaluationTest(lambda: reduce(mul, [1,2,3,4,5]))
        self.equivalentEvaluationTest(lambda: reduce(mul, [1,2,3,4,5], 0))

        def nonparallel(x):
            for v in x:
                yield v

        self.equivalentEvaluationTest(lambda: reduce(sub, nonparallel([1.0,2.0,3.0,4.0,5.0])))
        self.equivalentEvaluationTest(lambda: reduce(sub, nonparallel([1.0,2.0,3.0,4.0,5.0]), 10))

    def test_map_builtin(self):
        def addOne(x):
            return x + 1
        self.equivalentEvaluationTest(lambda: map(None, [1,2,3]))
        self.equivalentEvaluationTest(lambda: map(addOne, [1,2,3]))
        self.equivalentEvaluationTest(lambda: map(addOne, (x for x in [1,2,3])))

    def test_supported_builtin_member(self):
        import math
        def f(x):
            return x + math.pi

        self.equivalentEvaluationTest(f, 2)


    def test_enumerate(self):
        def f(x):
            return [_ for _ in x]

        self.equivalentEvaluationTest(f, [1,2,3])
        self.equivalentEvaluationTest(f, "asdf")

    def test_sorted_1(self):
        xs = [5, 2, 3, 1, 4]
        def f():
            return sorted(xs)

        self.equivalentEvaluationTest(f)

    def test_sorted_2(self):
        def f():
            return sorted(1)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)

    def test_sorted_3(self):
        xs = (5, 2, 3, 1, 4)
        def f():
            return sorted(xs)

        self.equivalentEvaluationTest(f)

    def test_sorted_4(self):
        xs = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10 }
        def f():
            return sorted(xs)

        self.equivalentEvaluationTest(f)

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


    def test_pass_returns_None(self):
        with self.create_executor() as executor:
            def f():
                pass

            self.assertIs(self.evaluateWithExecutor(f), None)


    def test_issubclass(self):
        test = self.equivalentEvaluationTestThatHandlesExceptions
        types = [float, int, bool, object, Exception]

        for t1 in types:
            for t2 in types:
                test(issubclass, t1, t2)
                test(issubclass, t1, (t2,))

    def test_isinstance_1(self):
        test = self.equivalentEvaluationTestThatHandlesExceptions

        for inst in [10, 10.0, True]:
            for typ in [float, object, int, bool]:
                test(lambda: isinstance(inst, typ))
                test(lambda: issubclass(type(inst), typ))

    def test_isinstance_2(self):
        class IsInstanceClass:
            pass

        def f():
            c = IsInstanceClass()
            return c.__class__ is IsInstanceClass and \
                not isinstance(c, list)

        self.equivalentEvaluationTest(f)

    def test_isinstance_3(self):
        class IsinstanceClassTest:
            pass

        def f():
            x = IsinstanceClassTest()
            return x.__class__ is IsinstanceClassTest and isinstance(x, IsinstanceClassTest)

        self.equivalentEvaluationTest(f)

    def test_sum_isPrime(self):
        def isPrime(p):
            x = 2
            while x*x <= p:
                if p%x == 0:
                    return 0
                x = x + 1
            return x

        self.equivalentEvaluationTest(lambda: sum(isPrime(x) for x in xrange(1000000)))

    def test_in_expr(self):
        x = [0,1,2,3]
        def f(arg):
            return arg in x

        for arg in range(-len(x), len(x)):
            self.equivalentEvaluationTest(f, arg)

    def test_notin_expr(self):
        def f(x):
            return x not in [2,3]

        for x in [2]:
            self.equivalentEvaluationTest(f, x)


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


    def test_pass(self):
        def passStatement():
            def f():
                pass

            x = f()
            return x

        self.equivalentEvaluationTest(passStatement)


    def test_inStatement_2(self):
        def inStatement():
            x = [0,1,2,3]
            return 0 in x

        self.equivalentEvaluationTest(inStatement)


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


    def test_print_is_noop(self):
        def f():
            print "hello world"
            return 10

        self.assertEqual(self.evaluateWithExecutor(f), 10)


    def test_import_sys(self):
        def f():
            import sys

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.ComputationError as e:
            self.assertIsInstance(e.message, str)
            self.assertIn(
                "Pyfora can't convert this code",
                e.message
                )


    def test_for_loop_values_carry_over(self):
        with self.create_executor() as executor:
            def f():
                y = 0
                for x in [1, 2, 3, 4]:
                    y = y + x

                return (y, x)

            self.equivalentEvaluationTest(f)


    def test_is_returns_true(self):
        self.equivalentEvaluationTest(lambda x: x is 10, 10)
        self.equivalentEvaluationTest(lambda x: x is 10, 11)


    def test_assert_1(self):
        def f():
            assert True

        self.equivalentEvaluationTest(f)

    def test_assert_2(self):
        def f():
            try:
                assert False, "omg"
            except AssertionError as e:
                return e.message

        self.equivalentEvaluationTest(f)

    def test_assert_3(self):
        def f():
            try:
                assert False
            except AssertionError as e:
                return e.message

        self.equivalentEvaluationTest(f)

    def test_assert_4(self):
        def f():
            try:
                assert False, 42
            except AssertionError as e:
                return e.message

        self.equivalentEvaluationTest(f)

    def test_assert_5(self):
        def f():
            return type(AssertionError("asdf"))

        self.equivalentEvaluationTest(f)


    def test_range_perf(self):
        ct = 1000
        while ct < 5000000:
            t0 = time.time()
            x = self.evaluateWithExecutor(range, ct)
            print (time.time() - t0), ct, ct / (time.time() - t0), " per second."

            ct = ct * 2
