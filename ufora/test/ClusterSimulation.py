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

import time
import logging
import os
import ufora.core.SubprocessRunner as SubprocessRunner
import traceback
import redis
import threading
import sys
import uuid

import ufora.util.KillProcessHoldingPort as KillProcessHoldingPort

import ufora.config.Setup as Setup

import ufora.util.DirectoryScope as DirectoryScope

import ufora.cumulus.distributed.CumulusGatewayRemote as CumulusGatewayRemote
import ufora.cumulus.distributed.CumulusActiveMachines as CumulusActiveMachines

import ufora.distributed.SharedState.Connections.TcpChannelFactory as TcpChannelFactory
import ufora.distributed.SharedState.Connections.ViewFactory as ViewFactory

import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager

import ufora.util.CodeCoverage as CodeCoverage

import ufora.native.CallbackScheduler as CallbackScheduler

WAIT_FOR_RELAY_TERMINATION_TIMEOUT_SECONDS = CodeCoverage.adjusted_timeout(20.0)

WAIT_FOR_SERVICE_TERMINATION_TIMEOUT_SECONDS = CodeCoverage.adjusted_timeout(30.0)

STOP_MESSAGE = "stop\n"


def simulationDirName():
    return os.path.join(Setup.config().fakeAwsBaseDir, time.strftime('%Y%m%d_%H-%M-%S'))

def makeUniqueDir():
    newDirName = simulationDirName()
    i = 0
    while os.path.exists(newDirName):
        newDirName = simulationDirName() + ('-%s' % i)
        i += 1
    logging.info('Starting ClusterSimulation in %s', newDirName)
    os.makedirs(newDirName)
    return newDirName


class WorkerProcesses(object):
    def __init__(self, worker_path):
        self.worker_path = worker_path
        self.desired = 0
        self.num_ever_started = 0
        self.processes = {}

    def desireNumberOfWorkers(self, count, blocking=False):
        logging.info('desiring %d workers', count)
        self.desired = count
        delta = count - len(self.processes)
        if delta > 0:
            self._addWorkers(delta)
        elif delta < 0:
            self._removeWorkers(-delta)

    def startService(self):
        pass

    def stopService(self):
        self._removeWorkers(len(self.processes))

    def _addWorkers(self, count):
        for _ in range(count):
            self._addWorker()

    def _removeWorkers(self, count):
        while count > 0:
            worker_id, (proc, thread, logfile) = self.processes.iteritems().next()
            del self.processes[worker_id]
            proc.stop()
            thread.join()
            logfile.close()
            count -= 1


    def _addWorker(self):
        worker_id = uuid.uuid4()
        log_path = self._workerLogFile(worker_id)
        logging.info("adding worker. script: %s, log: %s", self.worker_path, log_path)
        logfile = open(log_path, 'w')
        def writeline(msg):
            logfile.write(msg + '\n')
        env = dict(os.environ)
        env['UFORA_WORKER_BASE_PORT'] = str(30009 + 2*self.num_ever_started)
        env['UFORA_WORKER_CLUSTER_NAME'] = 'test'
        proc = SubprocessRunner.SubprocessRunner(
            [sys.executable, '-u', self.worker_path],
            writeline,
            writeline,
            env=env
            )
        thread = threading.Thread(target=self._runWorker, args=(worker_id,))
        self.processes[worker_id] = (proc, thread, logfile)
        thread.start()

    @staticmethod
    def _workerLogFile(worker_id):
        return os.path.join(Setup.config().fakeAwsBaseDir,
                            "worker-%s.log" % worker_id)

    def _runWorker(self, worker_id):
        while worker_id in self.processes:
            proc, _, logfile = self.processes[worker_id]
            logfile.write("***Starting worker***\n")
            logging.info("Starting worker %s", worker_id)
            logfile.flush()
            proc.start()
            proc.wait()




class Simulator(object):
    _globalSimulator = None
    _originalFakeAwsDir = None
    def __init__(self, user, password, clusterType="public"):
        callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
        self.callbackScheduler = callbackSchedulerFactory.createScheduler("Simulator", 1)

        self.uforaPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

        self.sharedStatePath = os.path.join(self.uforaPath, 'distributed/SharedState')
        self.sharedStateMainline = os.path.join(self.sharedStatePath, 'sharedStateMainline.py')

        self.gatewayServiceMainline = os.path.join(self.uforaPath, 'scripts/init/ufora-gateway.py')

        self.webPath = os.path.join(self.uforaPath, 'web/relay')
        self.relayScript = os.path.join(self.webPath, 'server.coffee')

        self.relayPort = Setup.config().relayPort
        self.relayHttpsPort = Setup.config().relayHttpsPort
        self.sharedStatePort = Setup.config().sharedStatePort
        self.restApiPort = Setup.config().restApiPort
        self.subscribableWebObjectsPort = Setup.config().subscribableWebObjectsPort

        self.user = user
        self.password = password

        # Specifies a namespace for cluster functionality available in the relay. Should be either
        # "public" or "dedicated".
        self.clusterType = clusterType

        self.desirePublisher = None
        self._connectionManager = None


    def dumpRelayLogs(self, user=None):
        if user is None:
            user = self.user

        try:
            logging.info("Reading from relay log at %s", self.relayLogFile)
            with open(self.relayLogFile, "r") as f:
                data = "\nRELAY> ".join(f.read().split("\n"))
                logging.error("Relay log:\n%s", data)
        except:
            logging.error("Failed to read the relay logs: %s\n", traceback.format_exc())


    @property
    def relayLogFile(self):
        return os.path.join(Setup.config().fakeAwsBaseDir, 'relay.log')

    @property
    def sharedStateLogFile(self):
        return os.path.join(Setup.config().fakeAwsBaseDir, 'sharedState.log')

    @property
    def gatewayLogFile(self):
        return os.path.join(Setup.config().fakeAwsBaseDir, 'ufora-gateway.log')

    @staticmethod
    def getGlobalSimulator():
        assert Simulator._globalSimulator is not None, 'Simulator has not been created yet'
        return Simulator._globalSimulator

    @staticmethod
    def createGlobalSimulator(useUniqueFakeAwsDir=True,
                              user='test',
                              password='asdfasdf',
                              clusterType="public"):
        # Mark our process as the process leader
        os.setpgid(0, 0)

        if not os.path.exists(Setup.config().fakeAwsBaseDir):
            os.makedirs(Setup.config().fakeAwsBaseDir)
        Simulator._originalFakeAwsDir = Setup.config().fakeAwsBaseDir
        if useUniqueFakeAwsDir:
            newDirName = makeUniqueDir()
            fakeAwsBase = Setup.config().fakeAwsBaseDir
            Setup.config().fakeAwsBaseDir = newDirName
            latestLinkPath = os.path.join(fakeAwsBase, 'latest')
            if os.path.exists(latestLinkPath):
                os.unlink(latestLinkPath)
            os.symlink(newDirName, latestLinkPath)

        assert Simulator._globalSimulator is None
        Simulator._globalSimulator = Simulator(user=user,
                                               password=password,
                                               clusterType=clusterType)
        return Simulator._globalSimulator

    def createCumulusGateway(self, callbackScheduler, vdm=None):
        if vdm is None:
            vdm = VectorDataManager.constructVDM(callbackScheduler)

        vdm.setDropUnreferencedPagesWhenFull(True)

        viewFactory = self.getViewFactory()
        return CumulusGatewayRemote.RemoteGateway(
            self.callbackScheduler,
            vdm,
            TcpChannelFactory.TcpStringChannelFactory(self.callbackScheduler),
            CumulusActiveMachines.CumulusActiveMachines(self.user, viewFactory),
            self.user,
            viewFactory
            )

    def verifySharedStateRunning(self, timeout=10.0):
        t0 = time.time()
        while True:
            try:
                self.getViewFactory().createView()
                return
            except:
                if time.time() - t0 >= timeout:
                    traceback.print_exc()
                    raise Exception("Couldn't verify SharedState has started")
            time.sleep(.1)


    def getViewFactory(self):
        return ViewFactory.ViewFactory.TcpViewFactory(self.callbackScheduler,
                                                      'localhost',
                                                      self.sharedStatePort)

    def startService(self):
        self.stopRelay()
        self.stopGatewayService()
        self.stopSharedState()
        KillProcessHoldingPort.killProcessGroupHoldingPorts(
            Setup.config().basePort,
            Setup.config().basePort + Setup.config().numPorts
            )

        self.createSimulationDirectory()

        self.startSharedState()

        try:
            self.startGatewayService()

            self.createTestAccount()

            logging.info('Starting relay')

            with DirectoryScope.DirectoryScope(self.webPath):
                self.startRelayProcess(self.relayScript)


            logging.info("verifying that shared state is running")

            self.verifySharedStateRunning()

            self.desirePublisher = WorkerProcesses(
                os.path.join(self.uforaPath, 'scripts/init/ufora-worker.py')
                )
        except:
            logging.error(
                "Couldn't start ClusterSimulation service. Exception=\n%s",
                traceback.format_exc()
                )
            self.dumpRelayLogs()
            raise

    def startSharedState(self):
        cacheDir = Setup.config().getConfigValue(
            "SHARED_STATE_CACHE", None
            )
        if cacheDir is None:
            logging.error("Expected shared state cache to have a value")
            cacheDir = os.path.join(Setup.config().fakeAwsBaseDir, 'ss_cache')

        logging.info("Starting shared state with cache dir '%s' and log file '%s'",
                     cacheDir,
                     self.sharedStateLogFile)

        with DirectoryScope.DirectoryScope(self.sharedStatePath):
            args = ['forever',
                    '--killSignal', 'SIGTERM',
                    '-l', self.sharedStateLogFile,
                    'start',
                    '-c', 'python', self.sharedStateMainline,
                    '--cacheDir', cacheDir,
                    '--logging', 'info'
                   ]

            def sharedStateStdout(msg):
                logging.info("SHARED STATE OUT> %s", msg)
            def sharedStateStderr(msg):
                logging.info("SHARED STATE ERR> %s", msg)

            startSharedState = SubprocessRunner.SubprocessRunner(
                args,
                sharedStateStdout,
                sharedStateStderr,
                dict(os.environ)
                )
            startSharedState.start()
            startSharedState.wait(60.0)
            startSharedState.stop()

    def stopSharedState(self):
        logging.info("Stopping SharedState")
        self.stopForeverProcess(self.sharedStateMainline)

    def restartSharedState(self):
        logging.info("Restarting SharedState")
        self.restartForeverProcess(self.sharedStateMainline)

    def startGatewayService(self):
        args = ['forever',
                '--killSignal', 'SIGTERM',
                '-l', self.gatewayLogFile,
                'start',
                '-c', 'python', self.gatewayServiceMainline,
                '--cluster-name', 'test']
        def gatewayStdout(msg):
            logging.info("GATEWAY OUT> %s", msg)
        def gatewayStderr(msg):
            logging.info("GATEWAY ERR> %s", msg)
        gatewayProc = SubprocessRunner.SubprocessRunner(
            args,
            gatewayStdout,
            gatewayStderr,
            dict(os.environ)
            )
        gatewayProc.start()
        gatewayProc.wait(60.0)
        gatewayProc.stop()

    def stopGatewayService(self):
        logging.info("Stopping Gateway Service")
        self.stopForeverProcess(self.gatewayServiceMainline)


    def stopRelay(self):
        logging.info("Stopping relay")
        self.stopForeverProcess(self.relayScript)

    @staticmethod
    def runForeverCommand(script, foreverCommand, timeout=60.0):
        args = ['forever', foreverCommand, script]
        def foreverStdOut(msg):
            logging.info("FOREVER(%s) OUT> %s", script, msg)
        def foreverStdErr(msg):
            logging.info("FOREVER(%s) ERR> %s", script, msg)
        subprocess = SubprocessRunner.SubprocessRunner(args,
                                                       foreverStdOut,
                                                       foreverStdErr,
                                                       dict(os.environ))
        subprocess.start()
        subprocess.wait(timeout)
        subprocess.stop()

    def stopForeverProcess(self, script, timeout=60.0):
        self.runForeverCommand(script, 'stop', timeout)

    def restartForeverProcess(self, script, timeout=60.0):
        self.runForeverCommand(script, 'restart', timeout)

    def startRelayProcess(self, relayScript):
        tries = 0

        while tries < 5:
            hasStartedEvent = self.tryToStartRelayProcess(relayScript)

            hasStartedEvent.wait(10.0)

            if hasStartedEvent.isSet():
                logging.info("Relay started")
                return

            logging.warn("Relay failed to start. Trying again")
            tries = tries + 1
            self.stopRelay()

        assert False, "Failed to start the relay."


    def tryToStartRelayProcess(self, relayScript):
        env = dict(os.environ)
        env['NODE_ENV'] = 'test'

        hasStartedEvent = threading.Event()

        def onStdOut(msg):
            hasStartedEvent.set()
            logging.info("RELAY STDOUT> %s", msg)

        def onStdErr(msg):
            logging.info("RELAY STDERR> %s", msg)

        coffeeCommand = 'coffee'
        if 'UFORA_DEBUG_RELAY' in os.environ:
            coffeeCommand = 'coffee-debug'

        nodejsOptions = []
        if 'UFORA_PROFILE_RELAY' in os.environ:
            nodejsOptions = ['--nodejs', '--prof']

        args = [relayScript,
                '--port', str(self.relayPort),
                '--gatewayport', str(self.subscribableWebObjectsPort)]

        command = ['forever',
                   '-f', '-l', self.relayLogFile,
                   'start',
                   '-c', coffeeCommand] + nodejsOptions + args

        SubprocessRunner.SubprocessRunner(command, onStdOut, onStdErr, env).start()
        return hasStartedEvent

    def getDesirePublisher(self):
        assert self.desirePublisher, "startService() hasn't been called on this Simulator"
        return self.desirePublisher

    @staticmethod
    def createSimulationDirectory():
        if not os.path.exists(Setup.config().fakeAwsBaseDir):
            os.makedirs(Setup.config().fakeAwsBaseDir)

    @staticmethod
    def createTestAccount():
        r = redis.StrictRedis()
        r.hmset("user:test", {
            "id": "test",
            "password": "$2a$10$PZW.M1.1p4BJpDDLhHIDd.2ROOdHAP40y4tdf5NBd48C7r3sqEGnS",
            "email": "test",
            "eula": "1",
            "role": "user",
            "first_name": "Test",
            "last_name": ""
            })
        r.hmset("user:test_dev", {
            "id": "test_dev",
            "password": "$2a$10$PZW.M1.1p4BJpDDLhHIDd.2ROOdHAP40y4tdf5NBd48C7r3sqEGnS",
            "email": "test",
            "eula": "1",
            "role": "dev",
            "first_name": "Test",
            "last_name": "Dev"
            })
        r.hmset("user:test_admin", {
            "id": "test_admin",
            "password": "$2a$10$PZW.M1.1p4BJpDDLhHIDd.2ROOdHAP40y4tdf5NBd48C7r3sqEGnS",
            "email": "test_admin",
            "eula": "1",
            "role": "admin",
            "first_name": "Test",
            "last_name": "Admin"
            })


    def stopService(self):
        self.stopGatewayService()
        self.stopSharedState()

        if self.desirePublisher:
            self.desirePublisher.stopService()
        if self._connectionManager:
            self._connectionManager.close()

        assert Simulator._globalSimulator is not None

        logging.info('shutting down relay')

        self.stopRelay()

        Simulator._globalSimulator = None
        Setup.config().fakeAwsBaseDir = Simulator._originalFakeAwsDir




