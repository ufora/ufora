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

import ufora.BackendGateway.SubscribableWebObjects.InMemorySocketIoJsonInterface as \
    InMemorySocketIoJsonInterface
import ufora.BackendGateway.SubscribableWebObjects.MessageProcessor as MessageProcessor
import ufora.config.Setup as Setup
import ufora.cumulus.distributed.CumulusGatewayInProcess as CumulusGatewayInProcess
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.distributed.SharedState.tests.SharedStateTestHarness as SharedStateTestHarness
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager

import pyfora.Connection as Connection


def create_executor():
    s3 = []
    def createMessageProcessor():
        harness = SharedStateTestHarness.SharedStateTestHarness(inMemory=True)

        ram_cache_size = Setup.config().computedValueGatewayRAMCacheMB * 1024 * 1024
        vdm = VectorDataManager.constructVDM(harness.callbackScheduler, ram_cache_size)

        with harness.viewFactory:
            cumulus_gateway = CumulusGatewayInProcess.InProcessGateway(
                harness.callbackScheduler.getFactory(),
                harness.callbackScheduler,
                vdm,
                pageSizeOverride=10000000,
                useInMemoryCache=200
                )

            #pull out the inmemory s3 interface so that we can surface it
            # and attach it to the connection object.
            s3.append(cumulus_gateway.s3Service)

        cache_loader = ComputedValueGateway.CacheLoader(
            harness.callbackScheduler,
            vdm,
            cumulus_gateway
            )

        return MessageProcessor.MessageProcessor(
            cumulus_gateway,
            cache_loader
            )

    socketIoToJsonInterface = InMemorySocketIoJsonInterface.InMemorySocketIoJsonInterface(
        createMessageProcessor
        )
    connection = Connection.connectGivenSocketIo(socketIoToJsonInterface)
    connection.__dict__['s3Interface'] = s3[0]
    connection.__dict__['socketIoToJsonInterface'] = socketIoToJsonInterface
    return connection

