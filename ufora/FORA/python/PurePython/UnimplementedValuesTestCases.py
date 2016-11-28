#   Copyright 2016 Ufora Inc.
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


import re
import traceback


class UnimplementedValuesTestCases(object):
    def test_typeWeCantTranslateYet_1(self):
        # we're not touching the bad value here, so we're still OK
        x = type(lambda x:x)
        def f():
            if False:
                return x
            return 0

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_2(self):
        # we're not touching the bad value here, so we're still OK
        import numpy
        def f():
            if False:
                return numpy
            return 0

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_3(self):
        # we're not touching the bad value here, so we're still OK
        import scipy
        def f():
            if False:
                return scipy.special
            return 0

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_4(self):
        # we're not touching the bad value here, so we're still OK
        import scipy
        def f():
            if False:
                return scipy.special.airy(0)
            return 0

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_class_1(self):
        import socket
        class C_test_typeWeCantTranslateYet_class_1:
            def wontCall(self):
                return socket
            def willCall(self):
                return 0

        c = C_test_typeWeCantTranslateYet_class_1()
        def f():
            return c.willCall()

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_class_2(self):
        import socket
        class C_test_typeWeCantTranslateYet_class_2:
            def wontCall(self):
                return socket
            def willCall(self):
                return 0

        def f():
            return C_test_typeWeCantTranslateYet_class_2().willCall()

        self.equivalentEvaluationTest(f)


    def test_typeWeCantTranslateYet_class_3(self):
        import scipy.special
        class C_test_typeWeCantTranslateYet_class_3:
            def wontCall(self):
                return scipy.special.airy(0)
            def willCall(self):
                return 0

        def f():
            return C_test_typeWeCantTranslateYet_class_3().willCall()

        self.equivalentEvaluationTest(f)

    def test_typeWeCantTranslateYet_raise_1(self):
        # note that this is different than trying to evaluate,
        # in pyfora code, type(lambda x:x).
        # that will give a completely different type of
        # error (an unhelpful runtime error). This test case
        # concerns errors that happen in PyObjectWalker
        with self.create_executor() as fora:
            x = type(lambda x:x)

            try:
                with fora.remotely:
                    y = x
                self.assertTrue(False)

            except Exceptions.UnconvertibleValueError as e:
                tracebackString = traceback.format_exc()
                pattern = ".*, in test_typeWeCantTranslateYet_raise_1" \
                          + "\\s*y = x\n" \
                          + "UnconvertibleValueError: " \
                          + "Pyfora didn't know how to convert x"
                self.assertIsNotNone(re.match(pattern, tracebackString, re.DOTALL), tracebackString)
                self.assertEqual("Pyfora didn't know how to convert x", str(e))

    def test_typeWeCantTranslateYet_raise_2(self):
        # note that this is different than trying to evaluate,
        # in pyfora code, type(lambda x:x).
        # that will give a completely different type of
        # error (an unhelpful runtime error). This test case
        # concerns errors that happen in PyObjectWalker
        x = type(lambda x:x)
        def f():
            return x

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            pattern = "Pyfora didn't know how to convert x.*\n" \
                      + ".*\\s*throw UnconvertibleValueError\\(\n" \
                      + ".*, in f\n" \
                      + "\\s*return x"
            self.assertIsNotNone(re.match(pattern, str(e)), str(e))
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

    def test_typeWeCantTranslateYet_raise_3(self):
        import numpy
        x = numpy
        def f():
            return x

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertTrue(
                str(e).startswith("Pyfora didn't know how to convert x")
                )
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

    def test_typeWeCantTranslateYet_raise_4(self):
        import scipy
        def f():
            x = scipy.special
            return 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertTrue(
                str(e).startswith("Pyfora didn't know how to convert scipy.special")
                )
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

    def test_typeWeCantTranslateYet_raise_5(self):
        import scipy.special
        def f():
            return scipy.special.airy(0)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertTrue(
                str(e).startswith("Pyfora didn't know how to convert scipy.special.airy")
                )
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

    def test_UnconvertibleValueErrorIsUncatchable(self):
        import scipy.special
        def f():
            try:
                return scipy.special.airy(0)
            except:
                return 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

    def test_UnconvertibleValueErrorIsUncatchable(self):
        import scipy.special
        def f():
            try:
                return scipy.special.airy(0)
            except:
                return 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except pyfora.ComputationError as e:
            self.assertIsInstance(
                e.remoteException,
                Exceptions.UnconvertibleValueError
                )

