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

import os
import os.path
import tempfile
import ufora.util.SubprocessingModified as subprocess
import shutil
import sys
import traceback
import threading
import ufora.core.SubprocessRunner as SubprocessRunner
import multiprocessing

import ufora
from ufora.util.DirectoryScope import DirectoryScope
import ufora.config.Setup as Setup

def removeFileIfExists(filePath):
    if os.path.isfile(filePath):
        os.remove(filePath)

def removeAndCreateDirectory(directory):
    if (os.path.isdir(directory)):
        shutil.rmtree(directory)
    os.mkdir(directory)

class TestScriptRunner(object):
    def __init__(self, testRoot, defaultTimeout=None):
        self.testRoot = os.path.join(os.path.split(os.path.split(ufora.__file__)[0])[0], testRoot)
        self.pathToBsaScripts = os.path.join(os.path.split(ufora.__file__)[0], "scripts")
        self.pathToProjectRoot = os.path.split(os.path.split(ufora.__file__)[0])[0]

        self.defaultTimeout = defaultTimeout or 500
        self.scripts = self.findTestScripts_()

        self.getTimeouts_()

    def getTimeouts_(self):
        self.timeouts = {}

        def walker(arg, dirname, fnames):
            for f in fnames:
                if f.endswith(".py"):
                    relpath = os.path.relpath(os.path.join(dirname,f), self.testRoot)

                    if relpath not in self.timeouts:
                        self.timeouts[relpath] = self.defaultTimeout

        os.path.walk(self.testRoot, walker, None)

    def getTimeout(self, abspath):
        relpath = os.path.relpath(abspath, self.testRoot)

        return self.timeouts[relpath]

    def findTestScripts_(self):
        scripts = []
        def walker(arg, dirname, fnames):
            for f in fnames:
                if f.endswith(".py"):
                    scripts.append(os.path.join(dirname,f))

        os.path.walk(self.testRoot, walker, None)
        return scripts


    def run(self):
        self.envVars = self.createTestEnvironment_()
        return self.run_()


    def runWithCodeCoverage(self):
        print "Setting up code coverage collection."
        self.createSiteCustomizeFileForCodeCoverage_()
        try:
            self.envVars = self.createTestEnvironment_()
            self.envVars["COVERAGE_PROCESS_START"] = self.coverageConfigFile_()
            allPassed = self.run_()
        finally:
            self.removeSiteCustomizeFile_()
            self.collectCoverageFiles_()

        return allPassed


    def run_(self):
        assert self.envVars is not None

        self.temporaryDirectory = tempfile.mkdtemp()
        try:
            self.tempConfigPath = os.path.join(self.temporaryDirectory, "config.cfg")
            self.envVars[Setup.DEFAULT_CONFIG_ENV_VARNAME] = self.tempConfigPath
            self.createTempConfigFile_()

            return self.runScripts_()
        finally:
            self.mergeTestResultFiles_()
            self.removeTemporaryDirectory_()

    def createTempConfigFile_(self):
        #write a fake config file with the necessary details
        with open(self.tempConfigPath, "wb") as f:
            f.write(self.generateTestConfigFileBody_())


    def generateTestConfigFileBody_(self):
        return ("ROOT_DATA_DIR = %s\n"
                "BASE_PORT = %s\n"
                "FORA_MAX_MEM_MB = %s\n"
                ) % (
                Setup.config().rootDataDir,
                Setup.config().basePort,
                "10000" if multiprocessing.cpu_count() <= 8 else "60000"
                )


    def createTestEnvironment_(self):
        envVars = dict(os.environ)
        envVars["PATH"] = self.pathToBsaScripts + os.pathsep + envVars["PATH"]
        envVars["PYTHONPATH"] = self.pathToProjectRoot + os.pathsep + envVars["PYTHONPATH"]
        envVars["UFORA_TEST_ERROR_OUTPUT_DIRECTORY"] = self.pathToProjectRoot
        return envVars


    def runScripts_(self):
        if len(self.scripts) == 0:
            print "NO TEST SCRIPTS FOUND IN:", self.testRoot
            return False

        scriptsThatFailed = []
        for s in self.scripts:
            if not self.runScript_(s):
                scriptsThatFailed.append(s)

        if scriptsThatFailed:
            print
            print
            print "SCRIPT FAILURE REPORT: ",
            print len(scriptsThatFailed), " scripts failed!"
            for s in scriptsThatFailed:
                print "\t", s
            return False

        return True

    def runScript_(self, script):
        print
        print "Running %s" % script
        print "with a timeout of ", self.getTimeout(script)

        if sys.platform == 'linux2':
            directory, filename = os.path.split(script)
            args = [sys.executable, "-u", '-c', "print 'started'; execfile('%s')" % filename]

            with DirectoryScope(directory):
                tries = 0
                runner = None

                while tries < 5 and runner is None:
                    startedEvent = threading.Event()

                    def printOutput(line):
                        if line == 'started':
                            startedEvent.set()
                            print "Script %s started" % filename
                        else:
                            print "OUT> %s\n" % line,

                    def printErr(line):
                        print "ERR> %s\n" % line,

                    runner = SubprocessRunner.SubprocessRunner(
                        args,
                        printOutput,
                        printErr,
                        self.envVars
                        )
                    runner.start()

                    startedEvent.wait(5)
                    if not startedEvent.isSet():
                        runner.terminate()
                        runner = None
                        tries = tries + 1
                        print "Retrying script ", filename, " as python failed to start."

                if runner is None:
                    print "Test %s failed to start a python process in 5 tries" % filename
                    return False
                else:
                    result = runner.wait(self.getTimeout(script))

                    if result is None:
                        try:
                            runner.terminate()
                        except:
                            print "Failed to terminate test runner: ", traceback.format_exc()
                        print "Test %s timed out" % filename,
                        return False
                    runner.stop()


                    if result != 0:
                        print "Test %s failed" % filename,
                        return False

                return True
        else:
            subprocess.check_call('cd "%s" & c:\python27\python.exe %s '
                % os.path.split(script),
                shell = True
                )

        return True
    def createSiteCustomizeFileForCodeCoverage_(self):
        self.removeSiteCustomizeFile_()

        with open(self.siteCustomizeFileName_(), 'w') as f:
            f.write('import coverage\n')
            f.write('coverage.process_startup()\n')


    def removeSiteCustomizeFile_(self):
        removeFileIfExists(self.siteCustomizeFileName_())
        removeFileIfExists(self.siteCustomizeFileName_() + 'c') # delete the .pyc file too


    def siteCustomizeFileName_(self):
        return os.path.join(self.pathToProjectRoot, 'sitecustomize.py')


    def coverageConfigFile_(self):
        return os.path.join(self.pathToProjectRoot, 'coverage.cfg')

    def mergeTestResultFiles_(self):
        print "Collecting test results."
        scriptDirectories = set([os.path.split(s)[0] for s in self.scripts])
        xunitFiles = [os.path.join(d, f) for d in scriptDirectories for f in os.listdir(d) if f.startswith('nosetests.') and f.endswith('.xml') ]
        index = 1
        for f in xunitFiles:
            try:
                shutil.move(f, self.pathToProjectRoot)
                index += 1
            except IOError:
                pass
        coreFiles = [os.path.join(d, f) for d in scriptDirectories for f in os.listdir(d) if f.startswith('core.') ]
        index = 1
        for f in coreFiles:
            try:
                shutil.move(f, self.pathToProjectRoot)
                index += 1
            except IOError:
                pass

    def collectCoverageFiles_(self):
        print "Collecting code coverage results."
        scriptDirectories = set([os.path.split(s)[0] for s in self.scripts])
        coverageFiles = [os.path.join(d, f) for d in scriptDirectories for f in os.listdir(d) if f.startswith('.coverage') ]
        index = 1
        for f in coverageFiles:
            try:
                shutil.move(f, os.path.join(self.pathToProjectRoot, '.coverage.' + str(index)))
                index += 1
            except IOError:
                pass


    def removeTemporaryDirectory_(self):
        shutil.rmtree(self.temporaryDirectory)

