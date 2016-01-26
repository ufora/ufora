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


import pyfora.pyAst.PyAstUtil as PyAstUtil

class FunctionTestCases:
    """Test cases for pyfora functions"""

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


    def test_define_function(self):
        def f(x):
            return x+1
        arg = 4

        with self.create_executor() as executor:
            f_proxy = executor.define(f).result()
            arg_proxy = executor.define(arg).result()

            res_proxy = f_proxy(arg_proxy).result()
            self.assertEqual(res_proxy.toLocal().result(), 5)


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


    def test_run_off_end_of_function_returns_None(self):
        with self.create_executor() as executor:
            def f():
                x = 10

            self.assertIs(self.evaluateWithExecutor(f), None)


    def test_empty_return_returns_None(self):
        with self.create_executor() as executor:
            def f():
                return

            self.assertIs(self.evaluateWithExecutor(f), None)


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


    def test_member_access(self):
        def g():
            return 10
        def f():
            return g().__str__()

        self.equivalentEvaluationTest(f)


    def test_loopsum(self):
        def loopSum(x):
            y = 0
            while x > 0:
                y = y + x
                x = x - 1
            return y

        for ix in range(3):
            self.equivalentEvaluationTest(loopSum, ix)

