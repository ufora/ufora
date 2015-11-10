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
            self.assertTrue(isinstance(e.exceptionValue, AttributeError))

    def test_exceptions_attribute_error_class(self):
        def f():
            class X:
                def f(self):
                    pass

            X().not_an_attribute

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.exceptionValue, AttributeError))

    def test_exceptions_attribute_error_translated_class_instance(self):
        def f():
            len.not_an_attribute

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.exceptionValue, AttributeError))

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
            self.assertTrue(isinstance(e.exceptionValue, Exception))
            self.assertEqual(e.exceptionValue.message, "hi")

    def test_exceptions_can_raise_UserWarning(self):
        def f():
            raise UserWarning("hi")

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertTrue(isinstance(e, pyfora.ComputationError))
            self.assertTrue(isinstance(e.exceptionValue, UserWarning))
            self.assertEqual(e.exceptionValue.message, "hi")

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
            self.assertIsInstance(e.exceptionValue, TypeError)

    def test_invalid_call_2(self):
        def f():
            return [1,2].__getitem__(3,4)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e.exceptionValue, TypeError)

    def test_list_append_exception_is_InvalidPyforaOperation(self):
        def f():
            [].append(10)

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.exceptionValue, pyfora.InvalidPyforaOperation)

    def test_IndexError_lists_1(self):
        def f():
            return [][100]

        with self.create_executor() as fora:
            e = fora.submit(f).result().toLocal().exception()
            self.assertIsInstance(e, pyfora.ComputationError)
            self.assertIsInstance(e.exceptionValue, IndexError)

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
            self.assertIsInstance(e.exceptionValue, IndexError)

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
            self.assertIsInstance(e.exceptionValue, IndexError)

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
