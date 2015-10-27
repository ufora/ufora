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

import logging
import traceback
import uuid
import time

import ufora.util.ManagedThread as ManagedThread

import ufora
import ufora.native.Hash as HashNative
import ufora.native.Cumulus as CumulusNative
import ufora.cumulus.distributed.CumulusGateway as CumulusGateway
import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines
import ufora.FORA.python.ModuleImporter as ModuleImporter

HANDSHAKE_TIMEOUT = 10.0

class RemoteGateway(CumulusGateway.CumulusGateway,
                    CumulusActiveMachines.CumulusActiveMachinesListener):
    def __init__(self,
                 callbackScheduler,
                 vdm,
                 channelFactory,
                 activeMachines,
                 username,
                 viewFactory):
        CumulusGateway.CumulusGateway.__init__(self,
                                               callbackScheduler,
                                               vdm,
                                               username,
                                               viewFactory)

        ModuleImporter.initialize()

        self.channelFactory_ = channelFactory

        self.connectedMachines_ = set()
        self.disconnectedMachines_ = set()
        self.desiredMachines_ = set()

        self.connectingThreads_ = []
        self.isTornDown_ = False

        self.activeMachines = activeMachines
        self.activeMachines.addListener(self)

        self.activeMachines.startService()

    def teardown(self):
        with self.lock_:
            self.isTornDown_ = True

        for thread in self.connectingThreads_:
            thread.join()

        self.stop()
        self.activeMachines.dropListener(self)
        self.activeMachines.stopService()

        CumulusGateway.CumulusGateway.teardown(self)

    def isConnected(self):
        return self.activeMachines.isConnected()

    def onWorkerAdd(self, ip, ports, machineIdAsString):
        machineId = CumulusNative.MachineId(HashNative.Hash.stringToHash(machineIdAsString))

        with self.lock_:
            if self.isTornDown_:
                return

            logging.info("CumulusClient %s preparing to connect to %s", self.cumulusClientId, machineId)
            self.desiredMachines_.add(machineId)

            newThread = ManagedThread.ManagedThread(
                target=self.addDesiredMachine,
                args=(machineId, ip, ports)
                )
            self.connectingThreads_.append(newThread)
            self.connectingThreads_ = [x for x in self.connectingThreads_ if x.isAlive()]

            newThread.start()

    def addDesiredMachine(self, machineId, ip, ports):
        tries = 0

        while not self.tryOnWorkerAdd(machineId, ip, ports):
            with self.lock_:
                if machineId not in self.desiredMachines_:
                    return

                if self.isTornDown_:
                    return

            tries += 1
            if tries > 4:
                logging.critical("Failed to connect to worker %s %s times. Bailing", machineId, tries)
                return
            else:
                time.sleep(1.0)

    def tryOnWorkerAdd(self, machineId, ip, ports):
        if self.isTornDown_:
            return False

        guid = HashNative.Hash.sha1(str(uuid.uuid4()))

        try:
            # TODO: get the number of cumulus ports from config
            assert len(ports) == 2

            channels = []
            for i in range(2):
                channel = self.connectToWorker(machineId, ip, ports[i], guid)
                assert channel is not None
                channels.append(channel)

            logging.info("CumulusClient %s successfully connected to both channels of  %s",
                self.cumulusClientId,
                machineId
                )

            with self.lock_:
                if machineId not in self.desiredMachines_:
                    return False


            with self.lock_:
                if machineId in self.disconnectedMachines_:
                    return True

                self.cumulusClient.addMachine(
                    machineId,
                    channels,
                    ModuleImporter.builtinModuleImplVal(),
                    self.callbackScheduler
                    )

                self.connectedMachines_.add(machineId)
                self.desiredMachines_.discard(machineId)

            return True
        except:
            logging.error("Failed: %s", traceback.format_exc())

            return False

    def connectToWorker(self, machineId, ip, port, guid):
        with self.lock_:
            stringChannel = self.channelFactory_.createChannel((ip, port))
            builtinsHash = ModuleImporter.builtinModuleImplVal().hash
            clientId = self.cumulusClientId
            callbackScheduler = self.callbackScheduler

        logging.info(
            "Client %s writing version message '%s' to %s",
            clientId,
            ufora.version,
            machineId
            )

        stringChannel.write(ufora.version)

        logging.info("Client %s writing client ID message to %s", clientId, machineId)

        stringChannel.write(machineId.__getstate__())

        logging.info("Client %s writing expected machineId message to %s", clientId, machineId)

        stringChannel.write(
            CumulusNative.CumulusClientOrMachine.Client(
                clientId
                ).__getstate__()
            )

        logging.info("Client %s writing guid %s to %s", clientId, guid, machineId)
        stringChannel.write(guid.__getstate__())

        channelAsQueue = stringChannel.makeQueuelike(callbackScheduler)
        msg = channelAsQueue.getTimeout(HANDSHAKE_TIMEOUT)
        if msg is None:
            logging.error(
                "While attempting to add worker %s, CumulusClient %s did not " +
                    "receive a builtin hash message during handshake",
                machineId,
                clientId
                )

        assert msg is not None

        logging.info("Client %s received serialized worker's builtin hash", clientId)

        try:
            workersBuiltinHash = HashNative.Hash(0)
            workersBuiltinHash.__setstate__(msg)
        except:
            logging.info("Client received a bad worker hash: %s of size %s", repr(msg), len(msg))
            raise

        builtinsAgree = workersBuiltinHash == builtinsHash

        if not builtinsAgree:
            logging.critical("Could not connect CumulusClient %s to CumulusWorker %s as they " + \
                             "have different builtins; client's builtin hash: %s, worker's " + \
                             "builtin hash: %s. Disconnecting channel",
                             clientId,
                             machineId,
                             builtinsHash,
                             workersBuiltinHash
                             )

            channelAsQueue.disconnect()
            return None

        return channelAsQueue

    def onReconnectedToSharedState(self):
        pass

    def onWorkerDrop(self, machineIdAsString):
        with self.lock_:
            machineId = CumulusNative.MachineId(HashNative.Hash.stringToHash(machineIdAsString))

            self.disconnectedMachines_.add(machineId)

            if machineId in self.desiredMachines_:
                self.desiredMachines_.discard(machineId)

            if machineId not in self.connectedMachines_:
                return

            self.connectedMachines_.discard(machineId)

            if len(self.connectedMachines_) == 0:
                self.onMachineCountWentToZero()

            self.cumulusClient.dropMachine(machineId)


