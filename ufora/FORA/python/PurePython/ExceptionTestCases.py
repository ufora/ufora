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
import pyfora


class ExceptionTestCases(object):
    def test_exceptions_can_translate_AttributeError(self):
        def f():
            return AttributeError

        self.assertIs(self.evaluateWithExecutor(f), AttributeError)

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
                "f() takes no arguments (1 given)"
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
                "f() takes exactly 1 argument (0 given)"
                )

    def test_invalid_call_6(self):
        def f(x, y):
            pass
            
        try:
            self.evaluateWithExecutor(f, 1, 2, 3)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "f() takes exactly 2 arguments (3 given)"
                )

    def test_invalid_call_7(self):
        def f(x, y=2):
            pass
            
        try:
            self.evaluateWithExecutor(f, 1, 2, 3)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(e.remoteException, TypeError)
            self.assertEqual(
                e.remoteException.message,
                "f() takes at most 2 arguments (3 given)"
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
                "f() takes at least 1 argument (0 given)"
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
                "f() takes at most 1 argument (2 given)"
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
                "f() takes at most 3 arguments (4 given)"
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
                "f() takes at least 2 arguments (1 given)"
                )

    def test_list_append_exception_is_InvalidPyforaOperation(self):
        def f():
            [].append(10)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.remoteException, pyfora.InvalidPyforaOperation)

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
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in test_free_vars_error_msg3\n" \
                    + "\\s*self\\.equivalentEvaluationTest.*\n" \
                    + ".*, in f\n" \
                    + "\\s*return x\\.y\\.z"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_free_vars_error_msg4(self):
        class C21:
            def f2():
                x = 42
                return x
            def f3():
                return x
        try:
            self.equivalentEvaluationTest(lambda: C21())
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in test_free_vars_error_msg4\n" \
                    + "\\s*self\\.equivalentEvaluationTest.*\n" \
                    + ".*, in f3\n" \
                    + "\\s*return x"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_free_vars_error_msg5(self):
        def f():
            return g()
        def g():
            return x.y.z
        try:
            self.equivalentEvaluationTest(f)
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'x'.*\n" \
                    + ".*, in f\n" \
                    + "\\s*return g\\(\\)\n" \
                    + ".*, in g\n" \
                    + "\\s*return x\\.y\\.z"
            self.assertTrue(re.match(pattern, str(e)) is not None)

    def test_with_block_free_vars_error_msg1(self):
        try:
            with self.create_executor() as fora:
                with fora.remotely.downloadAll():
                    missing_function()
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
        except pyfora.PythonToForaConversionError as e:
            pattern = ".*free variable 'z'.*\n" \
                    + ".*, in test_with_block_free_vars_error_msg2\n" \
                    + "\\s*foo\\(\\)\n" \
                    + ".*, in foo\n" \
                    + "\\s*return z"
            self.assertTrue(re.match(pattern, str(e)) is not None)

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

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(unconvertable, 2)

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

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.evaluateWithExecutor(f)

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

        with self.assertRaises(pyfora.PythonToForaConversionError):
            self.equivalentEvaluationTest(f)

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

