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

import ufora.BackendGateway.SubscribableWebObjects.InMemorySocketIoJsonInterface as InMemorySocketIoJsonInterface
import ufora.BackendGateway.SubscribableWebObjects.MessageProcessor as MessageProcessor
import ufora.cumulus.distributed.CumulusGatewayInProcess as CumulusGatewayInProcess
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import pyfora.Connection as Connection


def create_executor():
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

