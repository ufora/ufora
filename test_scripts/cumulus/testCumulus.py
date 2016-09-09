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

import tempfile
import unittest
import os
import logging

import ufora.FORA.python.FORA as FORA

import ufora.test.ClusterSimulation as ClusterSimulation
import ufora.test.CumulusSimulationUtils as CumulusSimulationUtils

import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory
import ufora.native.CallbackScheduler as CallbackScheduler

import ufora.cumulus.test.TestBase as TestBase


class CumulusServiceTests(unittest.TestCase, TestBase.CumulusTestCases):
    @classmethod
    def setUpClass(cls):
        cls.numWorkers = 2
        cls.simulator = ClusterSimulation.Simulator.createGlobalSimulator()
        cls.simulator.startService()
        cls.simulator.verifySharedStateRunning()

        cls.desirePublisher = cls.simulator.desirePublisher

        cls.desirePublisher.desireNumberOfWorkers(cls.numWorkers)

        FORA.initialize()

        cls.temporaryDirectoryName = tempfile.mkdtemp()
        cls.temporaryFileName = os.path.join(cls.temporaryDirectoryName, "temp.dat")
        cls.temporaryFileName2 = os.path.join(cls.temporaryDirectoryName, "temp2.dat")

        logging.info('CumulusServiceTests: getting remote gateway')
        cls.gateway = cls.simulator.createCumulusGateway(cls.simulator.callbackScheduler)
        logging.info('CumulusServiceTests: waiting for cumulus')
        CumulusSimulationUtils.waitCumulusReady(cls.gateway, cls.numWorkers)
        logging.info('CumulusServiceTests: cumulus is ready')

    @classmethod
    def tearDownClass(cls):
        cls.simulator.stopService()


if __name__ == '__main__':
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([])


