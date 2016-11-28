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

import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory
import pyfora.Exceptions as Exceptions
import pyfora.helpers as helpers

import unittest
import numpy
import sys


class EvaluateBodyAndReturnContext:
    def __enter__(self):
        pass

    def __exit__(self, excType, excValue, trace):
        pass

    def __pyfora_context_apply__(self, body):
        res = __inline_fora(
            """fun(@unnamed_args:(body), ...) {
                       body()
                       }"""
                )(body)

        return res

class WithRegularPython_test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executor = None

    @classmethod
    def tearDownClass(cls):
        if cls.executor is not None:
            cls.executor.close()

    @classmethod
    def create_executor(cls, allowCached=True):
        if not allowCached:
            return InMemorySimulationExecutorFactory.create_executor()
        if cls.executor is None:
            cls.executor = InMemorySimulationExecutorFactory.create_executor()
            cls.executor.stayOpenOnExit = True
        return cls.executor

    def test_internal_with_block_fails(self):
        with self.assertRaises(Exceptions.InvalidPyforaOperation):
            with self.create_executor() as fora:
                x = 5

                with fora.remotely:
                    z = 100

                    with z:
                        x = 100


    def test_basic_usage_of_with_block(self):
        with self.create_executor() as fora:
            x = 5

            with fora.remotely:
                z = 100

                with EvaluateBodyAndReturnContext():
                    z = z + x + 100


            result = z.toLocal().result()
            self.assertEqual(result, 205)

    def test_basic_out_of_process_1(self):
        with self.create_executor() as fora:
            x = 5

            with fora.remotely:
                with helpers.python:
                    z = x + 100

            result = z.toLocal().result()
            self.assertEqual(result, 105)

    def test_basic_out_of_process_2(self):
        with self.create_executor() as fora:
            x = 5

            with fora.remotely:
                z = 100

                with helpers.python:
                    z = z + x + 100

            result = z.toLocal().result()
            self.assertEqual(result, 205)

    def test_basic_out_of_process_list_comp(self):
        with self.create_executor() as fora:
            x = [1,2,3,4,5]

            with fora.remotely.downloadAll():
                def g(x):
                    return x + 1

                with helpers.python:
                    x = [g(i) for i in x]

            self.assertEqual(x, [2,3,4,5,6])

    def test_exception_marshalling(self):
        with self.assertRaises(UserWarning):
            with self.create_executor() as fora:
                with fora.remotely:
                    def g():
                        raise UserWarning("This is a user warning")
                    def f():
                        return g()

                    with helpers.python:
                        f()


    def test_basic_out_of_process_variable_identities(self):
        with self.create_executor() as fora:
            x = {}

            with fora.remotely.downloadAll():
                with helpers.python:
                    # 'x' is local to the with block - it won't be updated
                    x[10] = 20

                    # but the copy we send back will be because it gets
                    # duplicated back into the surrounding context
                    y = x

            self.assertEqual(x, {})
            self.assertEqual(y, {10:20})

    def test_functions_with_variables(self):
        aBoundVariable = 10
        def aFunc(x):
            return x + aBoundVariable

        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    # 'x' is local to the with block - it won't be updated
                    x = aFunc(20)

            self.assertEqual(x, 30)

    def test_module_references(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x = numpy.ones(10).shape[0]

            self.assertEqual(x, 10)

    def test_module_references_inside_of_functions(self):
        def f():
            # this can't work in pyfora right now
            z = {}
            z[10] = 10
            return numpy.ones(z[10]).shape[0]

        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x = f()

            self.assertEqual(x, 10)


    def test_module_references_inside_of_lambdas(self):
        f = lambda: numpy.ones(10).shape[0]

        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x = f()

            self.assertEqual(x, 10)

    def test_module_references_inside_of_class_functions(self):
        class AClassReferencingNumpy:
            def f(self):
                return numpy.ones(10).shape[0]

        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x = AClassReferencingNumpy().f()

            self.assertEqual(x, 10)

    def test_returning_builtin_from_out_of_process(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x = len

            self.assertEqual(x("asdf"), 4)

    def test_numpy_arrays_out_of_process(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                x = numpy.array([1, 2, 3, 4])

                with helpers.python:
                    x = x + x

            self.assertTrue(numpy.all(x == numpy.array([2, 4, 6, 8])))

    def test_with_block_in_loop(self):
        with self.create_executor() as fora:
            for sz in [1, 2, 3, 4]:
                with fora.remotely.downloadAll():
                    with helpers.python:
                        x = sz

                self.assertTrue(x == sz)

    def test_import_large_numpy_arrays(self):
        with self.create_executor() as fora:
            sz = 1000000

            with fora.remotely.downloadAll():
                with helpers.python:
                    x = numpy.ones(sz)
                x = sum(x)

            self.assertEqual(int(x), sz)

    def test_using_large_list_slices(self):
        with self.create_executor() as fora:
            
            with fora.remotely.downloadAll():
                l = range(10000000)

                aSlice = l[:10]

                with helpers.python:
                    x = sum(aSlice)

                aSlice = None

                l = None

            self.assertEqual(x, sum(range(10)))

    def test_can_open_files_in_regular_python(self):
        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    path = sys.modules['pyfora'].__file__

                    if path.endswith("pyc"):
                        path = path[:-1]

                    x = open(path, "rb").readline()

            self.assertTrue("Ufora Inc." in x)


            
    def test_class_chain_access(self):
        class A():
            def __init__(self):
                self.z = 10
        class B():
            def __init__(self):
                self.y = A()

        x = B()
        self.assertTrue(x.y.z == 10)

        with self.create_executor() as fora:
            with fora.remotely.downloadAll():
                with helpers.python:
                    x.y.z = 20
                    outX = x
        
        self.assertTrue(outX.y.z == 20)
