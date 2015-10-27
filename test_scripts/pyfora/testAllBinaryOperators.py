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

import pyfora.Exceptions
import ufora.FORA.python.PurePython.OperationsToTest as OperationsToTest
import unittest
import ufora.FORA.python.FORA as FORA
import pyfora.Connection as Connection
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.BackendGateway.SubscribableWebObjects.InMemorySocketIoJsonInterface as InMemorySocketIoJsonInterface
import ufora.BackendGateway.SubscribableWebObjects.MessageProcessor as MessageProcessor
import ufora.cumulus.distributed.CumulusGatewayInProcess as CumulusGatewayInProcess
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.FORA.python.PurePython.InMemoryExecutorTestCases as InMemoryExecutorTestCases
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness

class TestAllBinaryOperators(unittest.TestCase):
    def evaluateWithExecutor(self, func, *args, **kwds):
        shouldClose = True
        if 'executor' in kwds:
            executor = kwds['executor']
            shouldClose = False
        else:
            executor = self.create_executor()

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
        s3 = []
        def createMessageProcessor():
            harness = SharedStateTestHarness.SharedStateTestHarness(inMemory=True)

            def createCumulusComputedValueGateway():
                def createCumulusGateway(callbackScheduler, vdm):
                    with harness.viewFactory:
                        result = CumulusGatewayInProcess.InProcessGateway(
                            harness.callbackScheduler.getFactory(),
                            harness.callbackScheduler,
                            vdm
                            )

                        #pull out the inmemory s3 interface so that we can surface it and attach it to the connection
                        #object.

                        s3.append(result.s3Service)
                        return result

                return ComputedValueGateway.CumulusComputedValueGateway(
                    harness.callbackScheduler.getFactory(),
                    harness.callbackScheduler,
                    createCumulusGateway
                    )

            return MessageProcessor.MessageProcessor(
                harness.callbackScheduler,
                harness.viewFactory,
                createCumulusComputedValueGateway,
                {'id':'test','machine_ttl':3600}
                )

        socketIoToJsonInterface = InMemorySocketIoJsonInterface.InMemorySocketIoJsonInterface(createMessageProcessor)
        connection = Connection.connectGivenSocketIo(socketIoToJsonInterface)
        connection.__dict__['s3Interface'] = s3[0]
        return connection



    def equivalentEvaluationTestThatHandlesExceptions(self, executor, func, *args):
        try:
            r1 = func(*args)
            pythonSucceeded = True
        except Exception as ex:
            pythonSucceeded = False

        try:
            r2 = self.evaluateWithExecutor(func, *args, executor=executor)
            pyforaSucceeded = True
        except pyfora.Exceptions.ComputationError as ex:
            pyforaSucceeded = False

        self.assertEqual(pythonSucceeded, pyforaSucceeded)
        if pythonSucceeded:
            self.assertEqual(r1, r2)

    def test_all_binary_operations(self):
        with self.create_executor() as executor:
            arr = [1, 2, None, -4.4, 1e-6, -3.3e-4, "test", "", [], ["test"]]
            operations = OperationsToTest.OperationsToTest.allOperations()
            ct = len(arr)
            for idx1 in range(ct):
                for idx2 in range(ct):
                    v1 = arr[idx1]
                    v2 = arr[idx2]
                    for op in operations:
                        def f():
                            return op(v1, v2)
                        self.equivalentEvaluationTestThatHandlesExceptions(executor, f)


if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA])

