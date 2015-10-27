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
import os
import os.path
import socket
import tempfile
import time
import threading
import traceback
import shutil
import subprocess

import ufora.core.SubprocessRunner as SubprocessRunner
import ufora.distributed.ServerUtils.SimpleServer as SimpleServer
import ufora.distributed.util.common as common

from ufora.test.TestScriptRunner import TestScriptRunner

def createTestRunner(testDir='test_scripts/clusterperf'):
    assert 'TEST_LOOPER_MULTIBOX_OWN_IP' in os.environ
    assert 'TEST_LOOPER_MULTIBOX_IP_LIST' in os.environ
    assert 'TEST_LOOPER_TEST_ID' in os.environ
    assert 'BSA_DATA_DIR' in os.environ

    machinesInCluster = sorted(os.getenv('TEST_LOOPER_MULTIBOX_IP_LIST').split(' '))
    ownAddress = os.getenv('TEST_LOOPER_MULTIBOX_OWN_IP')
    assert ownAddress in machinesInCluster

    testId  = os.getenv('TEST_LOOPER_TEST_ID')

    testRunnerClass = MultiMachineMasterRunner if ownAddress == machinesInCluster[0] \
                      else MultiMachineWorkerRunner
    return testRunnerClass(machinesInCluster, ownAddress, testId, testDir)

def extractErrorMessagesFromLogfile(logfile, targetDir):  
    try:
        hasOne = False

        lineNumber = 0

        curBlock = []
        output = []

        def contains(msg):
            return " ERROR " in msg or " CRITICAL " in msg

        for line in open(logfile,"r"):
            lineNumber += 1

            if line[0] in (' ', '\t') or not curBlock:
                curBlock.append(line.rstrip())
            else:
                #found one - dump it
                if contains("\n".join(curBlock)):
                    output.append("\n".join(curBlock))

                curBlock = []
                
                curBlock.append(line.rstrip())


        if contains("\n".join(curBlock)):
            output.append("\n".join(curBlock))

        if output:
            fname = os.path.split(logfile)[1]
            fname_without_ext = os.path.splitext(fname)

            finalFname = os.path.join(targetDir, fname + "_errors.txt")

            with open(finalFname, "w") as resultFile:
                for o in output:
                    print >> resultFile, o
            logging.info(
                "Checked %s lines of %s to produce %s lines of error messages in %s",
                lineNumber,
                logfile,
                len(output),
                finalFname
                )
        else:
            logging.info("Checked %s lines of %s, but found no error messages", lineNumber, logfile)
    except:
        import traceback
        logging.error("Failed to extract error messages from %s:\n%s", logfile, traceback.format_exc())

class MultiMachineTestRunner(object):
    ProtoclVersion = '0.0.3'
    TestControlPort = 34532
    def __init__(self, machinesInCluster, ownAddress, testId, testDir):
        self.machinesInCluster = machinesInCluster
        self.ownAddress = ownAddress
        assert self.ownAddress in self.machinesInCluster

        self.testId  = testId
        self.testDir = testDir
        assert os.path.exists(self.testDir), "test directory '%s' does not exist" % self.testDir

    @property
    def clusterMaster(self):
        return self.machinesInCluster[0]

    @property
    def isClusterMaster(self):
        return self.clusterMaster == self.ownAddress

    @property
    def serviceName(self):
        assert False, "Must be implemented by derived class"

    def run_(self):
        assert False, "Must be implemented by derived class"

    def getInstallationEnvVars(self):
        envVars = {}
        try: 
            result = subprocess.check_output([
                'curl', 'http://169.254.169.254/latest/meta-data/local-ipv4',
                    '--connect-timeout', '1', '--silent', '-f']
                )
            envVars['UFORA_CLUSTER_HOST'] = result
            logging.info("resolved cluster host: %s", result)
        except:
            logging.warn("Failed to get public ip address from meta-data endpoint")

        return envVars
            
        

    def run(self):
        logging.info("machinesInCluster: %s, ownAddress: %s, master: %s, isMaster: %s",
            self.machinesInCluster, self.ownAddress, self.clusterMaster, self.isClusterMaster)

        try:
            self.rootDataDir = os.path.join(os.getenv('BSA_DATA_DIR'), 'on-prem-cluster')
            os.makedirs(self.rootDataDir)
            self.runInstallScript(self.serviceName, env=self.getInstallationEnvVars())
            return self.run_()
        except Exception as e:
            logging.error("Error running multi-machine test: %s\n%s", e, traceback.format_exc())
            return False
        finally:
            self.postExecutionCleanup()

    def postExecutionCleanup(self):
        self.removePath(os.path.join(self.rootDataDir, "cumulus_disk_storage"))

        logging.info("searching for logs in %s", os.path.join(self.rootDataDir, "logs"))
        
        for logfile in os.listdir(os.path.join(self.rootDataDir, "logs")):
            fullPath = os.path.join(self.rootDataDir, "logs", logfile)
            if os.path.isfile(fullPath):
                extractErrorMessagesFromLogfile(fullPath, os.getenv("LOOPER_DATA_DIR"))

        try:
            logDir = os.path.join(self.rootDataDir, "logs")
            targetLogPath = os.path.join(os.getenv("LOOPER_DATA_DIR"), "cumulus_logs.tar.gz")

            subprocess.call(['tar czf %s %s' % (targetLogPath, logDir)], shell=True)
        except:
            logging.error("Tried to copy %s to %s but failed: %s",
                logDir,
                targetLogDir,
                traceback.format_exc()
                )

    def removePath(self, path):
        for tries in range(3):
            try:
                shutil.rmtree(path)
                return True
            except:
                if tries == 2:
                    logging.warn("Failed to remove the path %s three times because:\n%s", path, traceback.format_exc())
        return False


    def runInstallScript(self, serviceName, env=None):
        args = [] if self.isClusterMaster else ['-c', self.clusterMaster]

        subprocess_env = dict(os.environ)
        if env is not None:
            subprocess_env.update(env)

        exitCode, stdOut, stdErr = SubprocessRunner.callAndReturnResultAndOutput(
                ['ufora/scripts/install/install-%s.sh' % serviceName, '-d', self.rootDataDir, '-s'] + args,
                env=subprocess_env
                )

        logging.info("install-%s.sh STDOUT> %s", serviceName, stdOut)
        logging.info("install-%s.sh STDERR> %s", serviceName, stdErr)
        if exitCode != 0:
            raise Exception("Failed to initialize %s. Exit code: %s.\nstdout: %s\nstderr: %s",
                    serviceName, exitCode, stdOut, stdErr)

        configFile = os.path.join(self.rootDataDir, 'config.cfg')
        assert os.path.exists(configFile), \
                "install-worker.sh failed to create config file in %s" % configFile

    def controlService(self, serviceName, controlArg):
        logging.info("Attempting to %s service %s", controlArg, serviceName)
        binDir = os.path.join(self.rootDataDir, 'bin')
        exitCode = self.runCommandAndLogOutput(binDir, serviceName, controlArg)
        if exitCode != 0:
            raise Exception("Failed to %s %s. Exit code: %s" % (controlArg, serviceName, exitCode))
        logging.info("Service %s successfully completed %s command", serviceName, controlArg)

    def runCommandAndLogOutput(self, path, command, *args):
        args = list(args)
        exitCode, stdOut, stdErr = SubprocessRunner.callAndReturnResultAndOutput(
                [os.path.join(path, command)] + args
                )
        logging.info("%s STDOUT> %s", command, stdOut)
        logging.info("%s STDERR> %s", command, stdErr)
        return exitCode


class MultiMachineWorkerRunner(MultiMachineTestRunner):
    def __init__(self, machinesInCluster, ownAddress, testId, testDir):
        super(MultiMachineWorkerRunner, self).__init__(
            machinesInCluster, ownAddress, testDir, testDir
            )

    @property
    def serviceName(self):
        return "worker"

    def run_(self):
        ''' This function starts the ufora worker and SLEEPS FOREVER.
        The process gets killed after the master machine reports its test result, as part
        of the test-looper heartbeat protocol.
        '''
        sock = None
        t0 = time.time()
        while not sock:
            sock = self.connectToMaster()
            if not sock:
                if time.time() - t0 > 60.0:
                    raise Exception("Failed to connect to master machine within specified timeout")
                time.sleep(1.0)
        try:
            self.startWorker()
            self.waitForStopCommand(sock)
        finally:
            logging.info("Stopping worker...")
            self.stopWorker()

    def connectToMaster(self):
        logging.info("Connecting to master at %s:%s",
                     self.clusterMaster,
                     MultiMachineWorkerRunner.TestControlPort
                     )
        while True:
            socketError = None
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.connect((self.clusterMaster, MultiMachineWorkerRunner.TestControlPort))
                common.writeString(sock, MultiMachineTestRunner.ProtoclVersion)
                common.writeString(sock, self.testId)
                response = common.readString(sock)
                if response != 'ok:start_worker':
                    logging.error("Error response from cluster master: %s", response)
                    sock.close()
                    sock = None
                    logging.info("Connected to cluster master. Response: %s", response)
                return sock
            except common.SocketException:
                socketError = traceback.format_exc()
            except socket.error:
                socketError = traceback.format_exc()

            if socketError:
                sock.close()
                logging.info("Waiting for master. %s", socketError)
                time.sleep(0.5)

    def waitForStopCommand(self, sock):
        message = common.readString(sock)
        if message != 'ok:stop_worker':
            logging.error("Expected stop command from server. Received: %s", message)
        else:
            logging.info("Received 'stop' command from master")

    def startWorker(self):
        self.controlService('ufora-worker', 'start')

    def stopWorker(self):
        self.controlService('ufora-worker', 'stop')


class MultiMachineMasterRunner(MultiMachineTestRunner):
    def __init__(self, machinesInCluster, ownAddress, testId, testDir):
        super(MultiMachineMasterRunner, self).__init__(
            machinesInCluster, ownAddress, testDir, testDir
            )
        self.testControlServer = SimpleServer.SimpleServer(MultiMachineMasterRunner.TestControlPort)
        self.testControlServer._onConnect = self.onConnect
        self.serverThread = None
        self.lock = threading.Lock()
        self.allWorkersConnectedEvent = threading.Event()
        if len(self.machinesInCluster) == 1:
            self.allWorkersConnectedEvent.set()
        self.connectedWorkers= []

    @property
    def serviceName(self):
        return "manager"

    def run_(self):
        try:
            self.startTestControlServer()
            self.createTestUser()
            self.waitForAllWorkers()
            self.startMaster()
            self.startWorkers()
            return self.runTests()
        finally:
            self.stopWorkers()
            self.stopMaster()
            self.stopTestControlServer()

    def startTestControlServer(self):
        logging.info("Starting test control service on port %s",
                     MultiMachineMasterRunner.TestControlPort
                     )
        self.serverThread = threading.Thread(target=self.serverListenLoop)
        self.serverThread.start()

    def serverListenLoop(self):
        while not self.testControlServer.shouldStop():
            try:
                self.testControlServer.runListenLoop()
            except socket.error as e:
                if e.errno == 98:
                    # address already in use
                    time.sleep(1.0)


    def stopTestControlServer(self):
        logging.info("Stopping test control server")
        self.testControlServer.stop()
        logging.info("waiting for server thread to join")
        self.serverThread.join()
        logging.info("Test control server stopped")


    def createTestUser(self):
        addUserCommand = os.path.join(self.rootDataDir, 'bin', 'addUser.py')
        exitCode, stdOut, stdErr = SubprocessRunner.callAndReturnResultAndOutput(
                [addUserCommand, '-e', 'test', '-p', 'asdfasdf', '-f', 'test', '-l', 'test', '-r']
                )
        logging.info("addUser.py STDOUT> %s", stdOut)
        logging.info("addUser.py STDERR> %s", stdErr)
        if exitCode != 0:
            raise Exception("Failed to create test user account")

    def waitForAllWorkers(self):
        logging.info("Waiting for all workers to come online")
        self.allWorkersConnectedEvent.wait()

    def startMaster(self):
        self.controlService('start', '')
        self.controlService('ufora-worker', 'start')

    def stopMaster(self):
        logging.info("Stopping ufora cluster")
        self.controlService('ufora-worker', 'stop')
        self.controlService('stop', '')

    def startWorkers(self):
        self.forEachWorker(
            lambda workerSocket: common.writeString(workerSocket, "ok:start_worker")
            )

    def stopWorkers(self):
        logging.info("Signalling all workers to stop")
        self.forEachWorker(
            lambda workerSocket: common.writeString(workerSocket, "ok:stop_worker")
            )

    def forEachWorker(self, func):
        for workerSocket, address in self.connectedWorkers:
            try:
                func(workerSocket)
            except socket.error:
                logging.error("Socket error from worker %s: %s", address, traceback.format_exc())
                workerSocket.close()

    def runTests(self):
        scriptRunner = TestScriptRunner(testRoot=self.testDir)
        return scriptRunner.run()

    def onConnect(self, workerSocket, address):
        host, port = address
        try:
            if not self.protocolHandshake(workerSocket):
                logging.error("Control protocol version mismatch. Worker: %s", host)
                self.endSession(workerSocket, 'error:protocol_version_mismatch')
            elif not host in self.machinesInCluster:
                logging.error("Unexpected worker. Worker: %s", host)
                self.endSession(workerSocket, 'error:unknown_worker_address')
            elif not self.verifyTestId(workerSocket):
                logging.error("Unexpected testId. Worker: %s.", host)
                self.endSession(workerSocket, 'error:test_id_mismatch')
            else:
                self.addConnectedWorker((workerSocket, host))
        except socket.error:
            logging.error("Socket error from worker %s: %s", host, traceback.format_exc())

    def protocolHandshake(self, workerSocket):
        workerVersion = common.readString(workerSocket)
        return workerVersion == MultiMachineTestRunner.ProtoclVersion

    def verifyTestId(self, workerSocket):
        workerTestId = common.readString(workerSocket)
        return workerTestId == self.testId

    def endSession(self, workerSocket, message=None):
        if message:
            common.writeString(workerSocket, message)
        workerSocket.close()

    def addConnectedWorker(self, worker):
        with self.lock:
            logging.info("Worker connectd: %s", worker)
            self.connectedWorkers.append(worker)
            if len(self.connectedWorkers) == len(self.machinesInCluster)-1:
                logging.info("All workers connected")
                self.allWorkersConnectedEvent.set()


