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

import re
import traceback
import pyfora
import pyfora.Exceptions as Exceptions


class ExceptionTestCases(object):
    def test_exceptions_can_translate_AttributeError(self):
        def f():
            return AttributeError

        self.assertIs(self.evaluateWithExecutor(f), AttributeError)

    def test_exceptions_can_translate_AssertionError(self):
        def f():
            return AssertionError

        self.assertIs(self.evaluateWithExecutor(f), AssertionError)

    def test_exceptions_can_translate_UserWarning(self):
        def f():
            return UserWarning

        self.assertIs(self.evaluateWithExecutor(f), UserWarning)

    def test_exceptions_type_of_UserWarning(self):
        def f():
            return UserWarning.__class__

        self.assertIs(self.evaluateWithExecutor(f), type(UserWarning))

    def test_exceptions_type_of_instantiated_UserWarning(self):
        def f():
            return type(UserWarning())

        self.assertIs(self.evaluateWithExecutor(f), type(UserWarning()))

    def test_exceptions_can_translate_UserWarning_instance_from_server(self):
        def f():
            return UserWarning("message")

        res = self.evaluateWithExecutor(f)

        self.assertTrue(isinstance(res, UserWarning))
        self.assertEqual(res.message, "message")
        self.assertEqual(res.args, ("message",))

    def test_exceptions_can_translate_UserWarning_instance_from_client(self):
        uw = UserWarning("message")
        def f():
            return UserWarning("message") is uw

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_exceptions_can_translate_type_and_object(self):
        def f():
            return (type, object, Exception)

        res = self.evaluateWithExecutor(f)

        self.assertIs(res[0], type)
        self.assertIs(res[1], object)
        self.assertIs(res[2], Exception)

    def test_exceptions_attribute_error_str(self):
        def f():
            "asdf".not_an_attribute

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.remoteException, AttributeError))

    def test_exceptions_attribute_error_class(self):
        def f():
            class X:
                def f(self):
                    pass

            X().not_an_attribute

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.remoteException, AttributeError))

    def test_exceptions_attribute_error_translated_class_instance(self):
        def f():
            len.not_an_attribute

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.remoteException, AttributeError))

    def test_exceptions_can_call_Exception(self):
        def f():
            return Exception("hi")

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().result()
            self.assertTrue(isinstance(e, Exception))
            self.assertEqual(e.message, "hi")

    def test_exceptions_Exception_object_has_class(self):
        def f():
            e = Exception("hi")
            return e.__class__

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().result()
            self.assertTrue(e is Exception)

    def test_exceptions_can_raise_Exception(self):
        def f():
            raise Exception("hi")

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.remoteException, Exception))
            self.assertEqual(e.remoteException.message, "hi")

    def test_exceptions_can_raise_UserWarning(self):
        def f():
            raise UserWarning("hi")

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.remoteException, UserWarning))
            self.assertEqual(e.remoteException.message, "hi")

    def test_exceptions_can_catch_UserWarning(self):
        def f():
            try:
                raise UserWarning("hi")
            except Exception as e:
                return e

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().result()
            self.assertTrue(isinstance(e, UserWarning))
            self.assertEqual(e.message, "hi")

    def test_exceptions_UserWarning_cannot_catch_Exception(self):
        def f():
            try:
                raise Exception("hi")
            except UserWarning as e:
                return None

        with self.create_executor() as fora:
            with self.assertRaises(pyfora.ComputationError):
                e = fora.submit(f).result().toLocal().result()

    def test_invalid_call_1(self):
        def f():
            10(10)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)

    def test_invalid_call_2(self):
        def f():
            return [1,2].__getitem__(3,4)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)

    def test_invalid_call_3(self):
        def f():
            return [1,2][1,2]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)

    def test_invalid_call_4(self):
        def f():
            pass

        try:
            self.evaluateWithExecutor(f, 1)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "call expression to function f() had too many unnamed arguments"
                )

    def test_invalid_call_5(self):
        def f(x):
            pass

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "couldn't match argument x in call to function f()"
                )

    def test_invalid_call_6(self):
        def g(x, y):
            pass

        try:
            self.evaluateWithExecutor(g, 1, 2, 3)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "call expression to function g() had too many unnamed arguments"
                )

    def test_invalid_call_7(self):
        def func(x, y=2):
            pass

        try:
            self.evaluateWithExecutor(func, 1, 2, 3)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "call expression to function func() had too many unnamed arguments"
                )

    def test_invalid_call_8(self):
        def f(x, y=2):
            pass

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "couldn't match argument x in call to function f()"
                )

    def test_invalid_call_9(self):
        def f(y=2):
            pass

        try:
            self.evaluateWithExecutor(f, 1, 2)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "call expression to function f() had too many unnamed arguments"
                )

    def test_invalid_call_10(self):
        def f(x,y,z=3):
            pass

        try:
            self.evaluateWithExecutor(f, 1, 2, 3, 4)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "call expression to function f() had too many unnamed arguments"
                )

    def test_invalid_call_11(self):
        def f(x,y,z=3):
            pass

        try:
            self.evaluateWithExecutor(f, 1)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "couldn't match argument y in call to function f()"
                )

    def test_invalid_call_12(self):
        def f(x, y):
            return x + y

        try:
            with self.create_executor() as executor:
                with executor.remotely:
                    f(x=2, y=3, z=4)
            self.assertTrue(False)
        except TypeError as e:
            self.assertEqual(
                e.message,
                "call expression to function f() had too many named arguments"
                )

    def test_invalid_call_13(self):
        def f(x, y):
            return x + y

        try:
            with self.create_executor() as executor:
                with executor.remotely:
                    f(2, y=3, z=4)
            self.assertTrue(False)
        except TypeError as e:
            self.assertEqual(
                e.message,
                "call expression to function f() had too many named arguments"
                )

    def test_invalid_call_14(self):
        class A_4324(object):
            def __init__(self, arg):
                self.arg = arg

        try:
            with self.create_executor() as executor:
                with executor.remotely:
                    A_4324(not_arg=42)
        except TypeError as e:
            self.assertEqual(
                e.message,
                "couldn't match argument arg in call to function A_4324()"
                )

    def test_dict_creation_error_1(self):
        def f():
            return dict([(1,2), (3,4,5)])

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, ValueError)
            self.assertEqual(
                e.remoteException.message,
                "dictionary update value 1 has more than 2 elements"
                )

    def test_dict_creation_error_2(self):
        def f():
            return dict([(1,2), (3,4), (5,)])

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, ValueError)
            self.assertEqual(
                e.remoteException.message,
                "dictionary update value 2 has fewer than 2 elements"
                )

    def test_dict_creation_error_3(self):
        def f():
            return dict([1])

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, ValueError)
            self.assertEqual(
                e.remoteException.message,
                "dictionary update value 0 is not iterable"
                )

    def test_dict_creation_error_4(self):
        def f():
            return dict(1)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "object is not iterable."
                )

    def test_list_append_exception_is_InvalidPyforaOperation_1(self):
        def f():
            [].append(10)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, pyfora.InvalidPyforaOperation)

            pattern = "Appending to a list is a mutating operation, " \
                      + "which pyfora doesn't support\.\n" \
                      + ".*throw InvalidPyforaOperation\\(\n" \
                      + ".*, in f\n" \
                      + "\\s*\\[\\]\.append\\(10\\)"
            self.assertIsNotNone(re.match(pattern, str(e), re.DOTALL))

    def test_list_append_exception_is_InvalidPyforaOperation_in_WithBlock(self):
        with self.create_executor() as fora:
            try:
                with fora.remotely:
                    x = []
                    x.append(42)
            except Exceptions.InvalidPyforaOperation as e:
                tracebackString = traceback.format_exc()
                pattern = ".* in test_list_append_exception_is_InvalidPyforaOperation_in_WithBlock\n" \
                          + "\\s*x\\.append\\(42\\)\n" \
                          + "InvalidPyforaOperation: Appending to a list is a " \
                          + "mutating operation, which pyfora doesn't support\\."
                self.assertIsNotNone(re.match(pattern, tracebackString, re.DOTALL))
                self.assertEqual(
                    str(e),
                    "Appending to a list is a mutating operation, which pyfora doesn't support."
                    )

    def test_extended_slices(self):
        # we're not supporting extended slices just yet
        def f():
            x = range(10)
            return x[1:2, 3:4]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, TypeError)

    def test_IndexError_lists_1(self):
        def f():
            return [][100]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, IndexError)

    def test_IndexError_lists_2(self):
        def f():
            return [][10]

        with self.create_executor() as fora:
            with self.assertRaises(IndexError):
                with fora.remotely:
                    f()

    def test_IndexError_tuples_1(self):
        def f():
            return (1,2)[100]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, IndexError)

    def test_IndexError_tuples_2(self):
        def f():
            return (1,2)[10]

        with self.create_executor() as fora:
            with self.assertRaises(IndexError):
                with fora.remotely:
                    f()

    def test_IndexError_strings_1(self):
        def f():
            return "asdf"[100]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, IndexError)

    def test_IndexError_strings_2(self):
        def f():
            return "asdf"[10]

        with self.create_executor() as fora:
            with self.assertRaises(IndexError):
                with fora.remotely:
                    f()

    def test_tuple_step(self):
        t = (1,2,3)
        def f():
            return t[::200]

        with self.create_executor() as fora:
            with self.assertRaises(NotImplementedError):
                with fora.remotely:
                    f()

    def test_free_vars_error_msg1(self):
        def f():
            return x
        try:
            self.equivalentEvaluationTest(f)
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in f\n" \
                    + "\\s*return x"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_free_vars_error_msg2(self):
        def f():
            return x.y.z
        try:
            self.equivalentEvaluationTest(f)
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in f\n" \
                    + "\\s*return x\\.y\\.z"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_free_vars_error_msg3(self):
        class C20:
            def f():
                return x.y.z

        try:
            self.equivalentEvaluationTest(lambda: C20())
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*unable to resolve free variable 'x'.*" \
                    + ".*, in f\n" \
                    + "\\s*return x\\.y\\.z"
            self.assertIsNotNone(re.match(pattern, str(e), re.DOTALL))

    def test_free_vars_error_msg4(self):
        class C21:
            def f2(self):
                x = 42
                return x
            def f3(self):
                return x
        try:
            self.equivalentEvaluationTest(lambda: C21())
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in f3\n" \
                    + "\\s*return x"
            self.assertIsNotNone(re.match(pattern, str(e)))

    def test_free_vars_error_msg5(self):
        def f():
            return g()
        def g():
            return x.y.z
        try:
            self.equivalentEvaluationTest(f)
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in g\n" \
                    + "\\s*return x\\.y\\.z"
            self.assertIsNotNone(re.match(pattern, str(e)))

    def test_with_block_free_vars_error_msg1(self):
        try:
            with self.create_executor() as fora:
                with fora.remotely.downloadAll():
                    missing_function()
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'missing_function'.*\n" \
                    + ".*, in test_with_block_free_vars_error_msg1\n" \
                    + "\\s*missing_function\\(\\).*"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_with_block_free_vars_error_msg2(self):
        def foo():
            return z

        try:
            with self.create_executor() as fora:
                with fora.remotely:
                    foo()
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*unable to resolve free variable 'z'.*" \
                    + ".*, in foo" \
                    + "\\s*return z"
            self.assertTrue(re.match(pattern, str(e), re.DOTALL) is not None)

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

    def test_divide_by_zero(self):
        with self.create_executor() as executor:
            def f(x):
                return 1/x
            arg = 0

            future = executor.submit(f, arg)
            with self.assertRaises(pyfora.PyforaError):
                future.result().toLocal().result()

    def test_reference_module(self):
        with self.create_executor() as executor:
            import socket
            def f():
                return str(socket)

            try:
                self.evaluateWithExecutor(f)
                self.assertTrue(False)
            except pyfora.ComputationError as e:
                pass

    def test_reference_nonexistent_module_member(self):
        import socket
        def f():
            return socket.this_doesnt_exist

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f)


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

            def g(x):
                return 1+f(x)

            try:
                self.evaluateWithExecutor(g,1)
                self.assertTrue(False)
            except pyfora.ComputationError as e:
                self.assertTrue(isinstance(e.remoteException, pyfora.InvalidPyforaOperation))


    def test_return_in_init_method(self):
        def f():
            class ClassReturnInInit:
                def __init__(self):
                    self.x = 10
                    return

            return ClassReturnInInit()

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

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

    def test_initMethods_5(self):
        def f():
            class A():
                def __init__(self, x):
                    self = 2
                    self.x = x
            return None

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

    def test_imports_3(self):
        import ufora.FORA.python.PurePython.testModules.ModuleWithUnconvertableMember \
            as ModuleWithUnconvertableMember

        def f(x):
            return ModuleWithUnconvertableMember.convertableMember(x)

        def unconvertable(x):
            return ModuleWithUnconvertableMember.unconvertableMember(x)

        with self.assertRaises(pyfora.Exceptions.ComputationError) as raised:
            self.equivalentEvaluationTest(unconvertable, 2)

        self.assertTrue(isinstance(raised.exception.remoteException, pyfora.Exceptions.InvalidPyforaOperation))

        self.equivalentEvaluationTest(f, 2)

    def test_only_convert_defs_and_string_constants_in_class_bodies(self):
        def f():
            class c:
                {"a":3}
                def m(self):
                    return 1

            return c().m()
        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test_free_variables_propagate_in_with_blocks(self):
        def f():
            return thisVariableDoesntExist

        with self.create_executor() as fora:
            with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
                with fora.remotely:
                    result = f()

    def test_unbound_variables_propagate_in_with_blocks(self):
        def f():
            x = x
            return x

        with self.create_executor() as fora:
            with self.assertRaises(UnboundLocalError):
                with fora.remotely:
                    result = f()

    def test_ellipsis(self):
        # we're not supporting Ellipsis yet in slicing
        def f():
            x = range(10)
            return x[...]

        with self.assertRaises(pyfora.ComputationError) as raised:
            self.evaluateWithExecutor(f)

        self.assertTrue(isinstance(raised.exception.remoteException, pyfora.Exceptions.InvalidPyforaOperation))

    def test_returning_slice_2(self):
        class C:
            def __getitem__(self, key):
                return key

        def f2():
            return C()[1:2:3]

        with self.assertRaises(pyfora.ForaToPythonConversionError):
            self.evaluateWithExecutor(f2)

    def test_inserting_slice_2(self):
        s = slice(1,2,3)
        def f():
            x = range(10)
            return x[s]

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            pass

    def test_yield_in_init_throws(self):
        class YieldInInit:
            def __init__(self):
                yield 10

        def f():
            YieldInInit()
            return

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test_properties_2(self):
        class C_with_properties_2:
            @property
            def prop(self, x):
                return x

        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(lambda: C_with_properties_2().prop)

    def test_cant_convert_property_itself(self):
        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(lambda: property)

    def test_assert_raises_1(self):
        msg = 1
        def f():
            assert False, msg

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, AssertionError)
            self.assertEqual(e.remoteException.message, msg)

    def test_assert_raises_2(self):
        msg = "asdf"
        def f():
            assert False, msg

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, AssertionError)
            self.assertEqual(e.remoteException.message, msg)

    def test_assert_raises_1(self):
        def f():
            assert False

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, AssertionError)
            self.assertEqual(e.remoteException.message, "")

    def test_cant_assign_to__inline_fora_in_pyfora(self):
        def f():
            __inline_fora = 42
            return __inline_fora

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test_free_vars_in_inline_fora_code_raise_exceptions(self):
        def f():
            x = 2
            inlineFun = __inline_fora("fun() { return x }")
            return inlineFun()

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test__inline_fora_in_non_call_expression_raises(self):
        def f():
            __inline_fora
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test_non_CreateFunction_expression_in__inline_fora_raises(self):
        def f():
            __inline_fora("1 + 1")
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test_non_string_arg_to__inline_fora_raises(self):
        def f():
            __inline_fora(1)
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test__inline_fora_as_function_arg_raises(self):
        def f(__inline_fora):
            return __inline_fora

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f, 0)

    def test___inline_fora_as_classname_raises_1(self):
        def f():
            class __inline_fora:
                pass
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test___inline_fora_as_classname_raises_2(self):
        class __inline_fora:
            pass

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(__inline_fora)

    def test___inline_fora_as_function_name_raises_1(self):
        def f():
            def __inline_fora():
                pass
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

    def test___inline_fora_as_function_name_raises_2(self):
        def __inline_fora():
            return 0

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(__inline_fora)

    def test_stray_self_in_init(self):
        class C_access_self_in_init:
            def __init__(self):
                str(self)

        def f():
            return C_access_self_in_init()

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.PythonToForaConversionError as e:
            self.assertTrue(
                e.message.startswith(
                    ("in pyfora __init__ methods, the self arg can "
                     "only appear in setattr or getattr expressions.")
                    )
                )

    def test_xrange_error_1(self):
        def f():
            return range(1.0)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)

    def test_xrange_error_2(self):
        def f():
            return range(1, 1.0)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)

    def test_xrange_error_3(self):
        def f():
            return range(1, 1, 1.0)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.remoteException, TypeError)
