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

import ufora.native.Hash as HashNative
import ufora.native.Cumulus as CumulusNative
import ufora.cumulus.distributed.CumulusGateway as CumulusGateway
import ufora.config.Setup as Setup
import ufora.native.StringChannel as StringChannelNative
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface

class InProcessGateway(CumulusGateway.CumulusGateway):
    def __init__(self, callbackSchedulerFactory, callbackScheduler, vdm, **kwds):
        #don't modify callers directly
        kwds = dict(kwds)

        if 's3Service' in kwds:
            s3Service = kwds['s3Service']
            del kwds['s3Service']
        else:
            s3Service = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        if 'threadsPerWorker' in kwds:
            threadsPerWorker = kwds['threadsPerWorker']
            del kwds['threadsPerWorker']
        else:
            threadsPerWorker = Setup.config().cumulusServiceThreadCount

        if 'memoryPerWorkerMB' in kwds:
            memoryPerWorkerMB = kwds['memoryPerWorkerMB']
            del kwds['memoryPerWorkerMB']
        else:
            memoryPerWorkerMB = 400


        if 'maxMBPerOutOfProcessPythonTask' in kwds:
            maxBytesPerOutOfProcessPythonTask = kwds['maxMBPerOutOfProcessPythonTask'] * 1024 * 1024
            del kwds['maxMBPerOutOfProcessPythonTask']
        else:
            maxBytesPerOutOfProcessPythonTask = None


        workerCount = 1
        if 'workerCount' in kwds:
            workerCount = kwds['workerCount']
            del kwds['workerCount']

        simulation = InMemoryCumulusSimulation.InMemoryCumulusSimulation(
            workerCount,
            0,
            s3Service=s3Service,
            memoryPerWorkerMB=memoryPerWorkerMB,
            callbackScheduler=callbackScheduler,
            threadsPerWorker=threadsPerWorker,
            maxBytesPerOutOfProcessPythonTask=maxBytesPerOutOfProcessPythonTask,
            **kwds
            )

        CumulusGateway.CumulusGateway.__init__(self,
                                               callbackScheduler,
                                               vdm,
                                               simulation.sharedStateViewFactory)

        self.s3Service = s3Service
        self.simulation = simulation

        self.viewFactory = self.simulation.sharedStateViewFactory

        for workerIx in xrange(workerCount):
            worker = self.simulation.getWorker(workerIx)
            workerVdm = self.simulation.getWorkerVdm(workerIx)

            channel1Client, channel1Worker = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)
            channel2Client, channel2Worker = StringChannelNative.InMemoryStringChannel(self.callbackScheduler)

            machineId = workerVdm.getMachineId()

            self.cumulusClient.addMachine(
                machineId,
                [channel1Client, channel2Client],
                ModuleImporter.builtinModuleImplVal(),
                self.callbackScheduler
                )

            worker.addCumulusClient(
                self.cumulusClientId,
                [channel1Worker, channel2Worker],
                ModuleImporter.builtinModuleImplVal(),
                self.callbackScheduler
                )

        self.worker = self.simulation.getWorker(0)
        self.workerVdm = self.simulation.getWorkerVdm(0)
        self.loadingService = self.simulation.loadingServices[0]


    def getClusterStatus(self):
        return {
            "workerCount": self.simulation.workerCount
            }


    def teardown(self):
        self.loadingService = None
        self.worker = None
        self.workerVdm = None
        self.viewFactory = None
        self.simulation.teardown()

        CumulusGateway.CumulusGateway.teardown(self)




