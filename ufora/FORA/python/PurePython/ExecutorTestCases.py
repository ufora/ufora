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

import math


class ExecutorTestCases(object):
    """ExecutorTestCases - mixin to define test cases for the pyfora Executor cass."""

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
            executor.objectRehydrator.convertEncodedStringToPythonObject = alwaysThrows

            func_proxy = executor.define(f).result()
            res_proxy = func_proxy().result()

            try:
                res_proxy.toLocal().result()
            except Exception as e:
                self.assertIsInstance(e, pyfora.PyforaError)
                self.assertIsInstance(e.message, MyException)
                self.assertEqual(e.message.message, errorMsg)


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

    def test_class_with_init(self):
        class HasInit(object):
            def __init__(self, x):
                self.x = x

            def get_x(self):
                return self.x

        def f(i):
            c = HasInit(i)
            return c.get_x()

        self.equivalentEvaluationTest(f, 1)

    def test_base_class_with_init_1(self):
        class HasInitBase(object):
            def __init__(self, x):
                self.x = x

            def get_x(self):
                return self.x

        class HasInitChild(HasInitBase):
            def __init__(self, x, y):
                HasInitBase.__init__(self, x)
                self.y = y

            def get_y(self):
                return self.y

        def f(i):
            c = HasInitChild(i, i+1)
            return (c.get_x(), c.get_y(), c.x, c.y)

        self.equivalentEvaluationTest(f, 1)

    def test_base_class_with_init_2(self):
        class HasInitBase_2(object):
            def __init__(self, x):
                self.x = x

            def get_x(self):
                return self.x

        class HasInitChild_2(HasInitBase_2):
            def __init__(self, x):
                #self.y = 2
                HasInitBase_2.__init__(self, x)

        def f(i):
            c = HasInitChild_2(i)
            return c.get_x()

        self.equivalentEvaluationTest(f, 1)

    def test_class_instance_with_init(self):
        class HasInit_1(object):
            def __init__(self, x):
                self.x = x

            def get_x(self):
                return self.x

        c = HasInit_1(1)
        def f():
            return c.get_x()

        self.equivalentEvaluationTest(f)

    def test_class_instance_with_init_to_python(self):
        class HasInit_2(object):
            def __init__(self, x):
                self.x = x

            def get_x(self):
                return self.x

        c = HasInit_2(1)
        def f():
            return c

        self.equivalentEvaluationTest(f, comparisonFunction=lambda a, b: a.x == b.x)


    def test_base_class_instance_with_init_to_python(self):
        class HasInitBase_3(object):
            def __init__(self, x):
                self.x = x

        class HasInitChild_3(HasInitBase_3):
            def __init__(self, x, y):
                HasInitBase_3.__init__(self, x)
                self.y = y

        c = HasInitChild_3(1, 'hello')
        def f():
            return c

        self.equivalentEvaluationTest(
            f,
            comparisonFunction=lambda a, b: a.x == b.x and a.y == b.y
            )


    def test_bound_method_from_base_class(self):
        class Base_1(object):
            def f(self, i):
                return i + 1

        class Child_1(Base_1):
            def g(self, i):
                return i

        b = Child_1()
        bound_method = b.f
        def f(i):
            return bound_method(i)

        self.equivalentEvaluationTest(f, 1)



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


    def test_inline_fora_1(self):
        val = 42
        def f():
            x = [val]
            ix = 0
            inlineFun = __inline_fora(
                """fun(@unnamed_args:(x, ix), *args) {
                       let y = x.__getitem__(ix);
                       y
                       }"""
                )
            x = inlineFun(x, ix)
            return x

        self.assertEqual(
            self.evaluateWithExecutor(f),
            val
            )

    def test_inline_fora_2(self):
        val = 42
        def f():
            inlineFun1 = __inline_fora(
                "fun(*args) { return MutableVector.create(2, 0) }"
                )
            mutableVec = inlineFun1()

            __inline_fora(
                "fun(@unnamed_args:(m, val), *args) { m[0] = val }"
                )(mutableVec, val)

            inlineFun3 = __inline_fora(
                "fun(@unnamed_args:(m), *args) { return m[0] }"
                )
            return inlineFun3(mutableVec)

        self.assertEqual(
            self.evaluateWithExecutor(f),
            val
            )

    def test_inline_fora_mutable_thing(self):
        class C_inline:
            def __init__(self, sz):
                self.m = __inline_fora(
                    """fun(@unnamed_args:(sz), *args) {
                           MutableVector.create(sz.@m, 0)
                           }"""
                   )(sz)

            def setitem(self, val, ix):
                __inline_fora(
                    """fun(@unnamed_args:(m, val, ix), *args) {
                        m[ix.@m] = val
                        }"""
                    )(self.m, val, ix)

            def getitem(self, ix):
                return __inline_fora(
                    """fun(@unnamed_args:(m, ix), *args) {
                           m[ix.@m]
                           }"""
                    )(self.m, ix)

        val = 42
        def f():
            c = C_inline(10)
            ix = 5
            c.setitem(val, ix)
            return c.getitem(ix)

        self.assertEqual(self.evaluateWithExecutor(f), val)

    def test_inline_fora_access_pyfora_builtins(self):
        def f():
            return __inline_fora(
                """fun(@unnamed_args:(ix), *args) {
                       return PyInt(1) + ix
                       }"""
                )(2)

        self.assertEqual(
            self.evaluateWithExecutor(f),
            3
            )

    def test_inline_fora_access_fora_builtins_1(self):
        def f(x):
            sinFunc = __inline_fora(
                """fun(@unnamed_args:(x), *args) {
                       PyFloat(math.sin(x.@m))
                       }"""
                )
            return sinFunc(x)

        arg = 0.0
        self.assertEqual(
            self.evaluateWithExecutor(f, arg),
            math.sin(arg)
            )

    def test_inline_fora_access_fora_builtins_2(self):
        def f(x):
            return __inline_fora(
                """fun(@unnamed_args:(x), *args) {
                       purePython.PyFloat(builtin.math.sin(x.@m))
                       }"""
                )(x)

        arg = 0.0
        self.assertEqual(
            self.evaluateWithExecutor(f, arg),
            math.sin(arg)
            )

