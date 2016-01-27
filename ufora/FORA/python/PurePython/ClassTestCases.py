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

import pyfora.Exceptions as Exceptions

class ClassTestCases(object):
    """Test cases for pyfora classes"""

    def test_str_on_class(self):
        def f():
            class StrOnClass:
                def __str__(self):
                    return "special"
            return str(StrOnClass())

        self.equivalentEvaluationTest(f)


    def test_class_pass(self):
        def f():
            class X:
                pass

        self.equivalentEvaluationTest(f)


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


    def test_returnClasses(self):
        class ReturnedClass:
            def __init__(self, x):
                self.x = x

        def f(x):
            return ReturnedClass(x)

        shouldBeReturnedClass = self.evaluateWithExecutor(f, 10)

        self.assertEqual(shouldBeReturnedClass.x, 10)
        self.assertEqual(str(shouldBeReturnedClass.__class__), str(ReturnedClass))


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