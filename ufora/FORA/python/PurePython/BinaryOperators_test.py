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
import pyfora.Connection as Connection


import ufora.FORA.python.PurePython.OperationsToTest as OperationsToTest
import ufora.BackendGateway.SubscribableWebObjects.InMemorySocketIoJsonInterface as InMemorySocketIoJsonInterface
import ufora.BackendGateway.SubscribableWebObjects.MessageProcessor as MessageProcessor
import ufora.cumulus.distributed.CumulusGatewayInProcess as CumulusGatewayInProcess
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness

import ufora.FORA.python.PurePython.InMemorySimulationExecutorFactory as \
    InMemorySimulationExecutorFactory

import unittest
import logging
import traceback


class TestAllBinaryOperators(unittest.TestCase):
    def evaluateWithExecutor(self, func, *args, **kwds):
        shouldClose = True
        if 'executor' in kwds:
            executor = kwds['executor']
            shouldClose = False
        else:
            executor = InMemorySimulationExecutorFactory.create_executor()

        try:
            func_proxy = executor.define(func).result()
            args_proxy = [executor.define(a).result() for a in args]
            res_proxy = func_proxy(*args_proxy).result()

            result = res_proxy.toLocal().result()
            return result
        except Exception as ex:
            raise ex
        finally:
            if shouldClose:
                executor.close()

    def create_executor(self):
        return InMemorySimulationExecutorFactory.create_executor()

    def equivalentEvaluationTestThatHandlesExceptions(self, executor, func, *args):
        try:
            py_res = func(*args)
            pythonSucceeded = True
        except Exception as ex:
            pythonSucceeded = False

        try:
            pyfora_res = self.evaluateWithExecutor(func, *args, executor=executor)
            pyforaSucceeded = True
        except pyfora.ComputationError as ex:
            pyforaSucceeded = False

        self.assertEqual(pythonSucceeded, pyforaSucceeded)
        if pythonSucceeded:
            self.assertEqual(py_res, pyfora_res)
            self.assertEqual(type(py_res), type(pyfora_res))
            return py_res

    def test_division_rounding(self):
        with self.create_executor() as executor:
            arr = [1, 2, -4.4, 1e-6, -3.3e-4, -1, -2, 0, 0.0]
            ct = len(arr)
            for idx1 in range(ct):
                for idx2 in range(ct):
                    v1 = arr[idx1]
                    v2 = arr[idx2]
                    def f():
                        return v1 / v2
                    self.equivalentEvaluationTestThatHandlesExceptions(executor, f)

    def test_all_binary_operations(self):
        with self.create_executor() as executor:
            arr = [1, 2, -2, None, -4.4, 1e-6, -3.3e-4, "test", "", [], ["test"]]
            operations = OperationsToTest.OperationsToTest.allOperations()
            ct = len(arr)
            for idx1 in range(ct):
                for idx2 in range(ct):
                    v1 = arr[idx1]
                    v2 = arr[idx2]
                    for op in operations:
                        def f():
                            return op(v1, v2)

                        try:
                            self.equivalentEvaluationTestThatHandlesExceptions(executor, f)
                        except:
                            logging.critical(
                                "incompatible python/pyfora behavior in call %s(%s, %s)",
                                op.__name__, repr(v1), repr(v2)
                                )
                            raise
