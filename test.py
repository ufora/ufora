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

#!/usr/bin/python
"""
This is the primary unit-test entrypoint for the FORA project. It runs a battery
of C++ and python unit-tests.
"""
import sys
import logging
import unittest
import os
import re
import time
import nose
import nose.config
import nose.loader
import nose.plugins.manager
import nose.plugins.xunit
import argparse
import hashlib

import ufora
import ufora.config.Mainline as Mainline

import ufora.util.AssertStableThreadCount as AssertStableThreadCount
import ufora.util.SubprocessingModified as subprocess

import ufora.FORA.python.FORA as FORA
import ufora.FORA.test.test as FORASemanticsTest
import ufora.FORA.test.localperf as LocalPerfTest
import ufora.native

import ufora.config.Setup as Setup
import ufora.util.CodeCoverage as CodeCoverage
import ufora.test.UnitTestCommon as UnitTestCommon

import ufora.test.MultiMachineTestRunner as MultiMachineTestRunner
from ufora.test.TestScriptRunner import TestScriptRunner
from ufora.test.OutputCaptureNosePlugin import OutputCaptureNosePlugin

hexDict = {
    'a': 10,
    'b': 11,
    'c': 12,
    'd': 13,
    'e': 14,
    'f': 15,
    '0': 0,
    '1': 1,
    '2': 2,
    '3': 3,
    '4': 4,
    '5': 5,
    '6': 6,
    '7': 7,
    '8': 8,
    '9': 9
    }

def hexToInt(hexString):
    val = 0
    for char in hexString:
        val = val * 16 + hexDict[char]
    return val

class OrderedFilterAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not 'ordered_actions' in namespace:
            setattr(namespace, 'ordered_actions', [])
        previous = namespace.ordered_actions
        previous.append((self.dest, values))
        setattr(namespace, 'ordered_actions', previous)

class UnitTestArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super(UnitTestArgumentParser,self).__init__(add_help = True)
        self.subsetsGroup = self.add_argument_group(
                title = 'Test Subgroups',
                description = 'Parameters that specify which test subgroups to run')

        self.subsetsGroup.add_argument('-lang',
                    action = 'store_true',
                    help = 'run the FORA language unit tests',
                    default = False)
        self.subsetsGroup.add_argument('-py',
                    action = 'store_true',
                    help = 'run the python unit tests',
                    default = False)
        self.subsetsGroup.add_argument('-scripts',
                    action = 'store_true',
                    help = 'run the script unit tests',
                    default = False)
        self.subsetsGroup.add_argument('--scriptPath',
                    help = 'specific path to search for python files for script tests',
                    type=str,
                    default = None
                    )
        self.subsetsGroup.add_argument('-native',
                    nargs = '?',
                    help = 'run only native tests matching NATIVE',
                    const = True,
                    default = False)
        self.subsetsGroup.add_argument('-profile',
                    help = 'profile the program',
                    default = None,
                    type=str
                    )
        self.subsetsGroup.add_argument('-node',
                    action = 'store_true',
                    help = 'run the node.js unit tests',
                    default = False)
        self.subsetsGroup.add_argument('-localperf',
                    action = 'store_true',
                    help = 'run the local perf unit tests',
                    default = False
                    )
        self.subsetsGroup.add_argument('-multibox',
                    action = 'store_true',
                    help = 'run the multi-box tests',
                    default = False
                    )
        self.subsetsGroup.add_argument('-browser',
                    action = 'store_true',
                    help = 'run the end-to-end browser tests',
                    default = False
                    )

        self.testParametersGroup = self.add_argument_group(
                title = 'test.py parameters',
                description = 'Parameters specific to test.py')

        self.testParametersGroup.add_argument('-list',
                    action = 'store_true',
                    help = 'list any python unittests rather than running them',
                    default = False)
        self.testParametersGroup.add_argument('-random',
                    action = 'store_true',
                    help = 'randomize test ordering',
                    default = False)
        self.testParametersGroup.add_argument('-copies',
                    type = int,
                    help = 'run each test case NUM times',
                    default = 1)
        self.testParametersGroup.add_argument('-langfilter',
                    type = str,
                    help = 'only run langtests where the module or testname contains this string',
                    default = None)
        self.testParametersGroup.add_argument('-repeat',
                    action = 'store_true',
                    help = 'run the test suite repeatedly',
                    default = False)
        self.testParametersGroup.add_argument('-pythreadcheck',
                    action = 'store_true',
                    help = 'run each python unit test-case in a thread-checking scope',
                    default = False)
        self.testParametersGroup.add_argument('-modpair',
                    nargs = 2,
                    help = "filter the test list 'x' as x[o::m], e.g. starting with 'o' and taking every mth test. Useful for finding subsets of tests causing problems.",
                    type = int,
                    default = None)
        self.testParametersGroup.add_argument('-timeout',
                    type = float,
                    nargs = 1,
                    help = 'fail test if not completed after TIMEOUT seconds',
                    default = None
                    )

    def parse_args(self, args):
        argholder = super(UnitTestArgumentParser,self).parse_known_args(args)
        args = argholder[0]
        setattr(args, 'remainder', argholder[1])
        return args

def composeSemanticFilter(f1, f2):
    def filter(moduleName, testName):
        return f1(moduleName, testName) and f2(moduleName, testName)
    return filter

def semanticFilterContainingString(string):
    def filter(moduleName, testName):
        return string in (moduleName + "." + testName)
    return filter

def alwaysTrueSemanticFilter(moduleName, testName):
    return True

def semanticFilterModpair(modTarget, modVal):
    def filter(moduleName, testName):
        hashval = hexToInt(hashlib.sha1(repr(moduleName + "." + testName)).hexdigest())

        return hashval % modVal == modTarget
    return filter

def makeSemanticsTestFilter(args):
    filterFun = alwaysTrueSemanticFilter

    if args.langfilter:
        filterFun = composeSemanticFilter(
            filterFun,
            semanticFilterContainingString(args.langfilter)
            )

    if args.modpair:
        filterFun = composeSemanticFilter(
            filterFun,
            semanticFilterModpair(args.modpair[0], args.modpair[1])
            )

    return filterFun

class PythonTestArgumentParser(argparse.ArgumentParser):
    def __init__(self):
        super(PythonTestArgumentParser,self).__init__(add_help = False)
        self.add_argument('-filter',
                            nargs = 1,
                            help = 'restrict python unittests to a subset matching FILTER',
                            action = OrderedFilterAction,
                            default = None)
        self.add_argument('-add',
                            nargs = 1,
                            help = 'add back tests matching ADD',
                            action = OrderedFilterAction,
                            default = None)
        self.add_argument('-exclude',
                            nargs = 1,
                            help = "exclude python unittests matching 'regex'. These go in a second pass after -filter",
                            action = OrderedFilterAction,
                            default = None)
    def parse_args(self,toParse):
        argholder = super(PythonTestArgumentParser,self).parse_args(toParse)
        args = None
        if 'ordered_actions' in argholder:
            args = []
            for arg,l in argholder.ordered_actions:
                args.append((arg,l[0]))
        return args




def regexMatchesSubstring(pattern, toMatch):
    for x in re.finditer(pattern, toMatch):
        return True
    return False


def applyFilterActions(filterActions, tests):
    filtered = [] if filterActions[0][0] == 'add' else list(tests)

    for action, pattern in filterActions:
        if action == "add":
            filtered += [x for x in tests if
                                    regexMatchesSubstring(pattern, x.id())]
        elif action == "filter":
            filtered = [x for x in filtered if
                                    regexMatchesSubstring(pattern, x.id())]
        elif action == "exclude":
            filtered = [x for x in filtered if
                                    not regexMatchesSubstring(pattern, x.id())]
        else:
            assert False

    return filtered


def printTests(testCases):
    for test in testCases:
        print test.id()

def runPyTestSuite(config, testFiles, testCasesToRun, testArgs):
    cov = startCoverageCollectionIfEnabled()

    with AssertStableThreadCount.AssertStableThreadCount():
        testProgram = nose.core.TestProgram(
            config=config,
            defaultTest=testFiles,
            suite=testCasesToRun,
            argv=testArgs,
            exit=False
            )

    stopCoverageCollectionIfEnabled(cov)
    return not testProgram.success


def runPythonUnitTests(args, testFilter):
    """run python unittests in all *_test.py files in the project.

    Args contains arguments from a UnitTestArgumentParser.

    Returns True if any failed.
    """
    bsaRootDir = os.path.split(ufora.__file__)[0]

    return runPythonUnitTests_(
        args, testFilter, testGroupName = "python",
        testFiles = UnitTestCommon.findTestFiles(bsaRootDir, '.*_test.py$')
        )

def runPythonUnitTests_(args, testFilter, testGroupName, testFiles):
    testArgs = ["dummy"]

    if args.testHarnessVerbose or args.list:
        testArgs.append('--nocaptureall')

    testArgs.append('--verbosity=0')

    if not args.list:
        print "Executing %s unit tests." % testGroupName

    Setup.config().configureLoggingForUserProgram()

    parser = PythonTestArgumentParser()
    filterActions = parser.parse_args(args.remainder)

    bsaRootDir = os.path.split(ufora.__file__)[0]

    testCasesToRun = []

    plugins = nose.plugins.manager.PluginManager([OutputCaptureNosePlugin()])

    config = nose.config.Config(plugins=plugins)
    config.configure(testArgs)
    for i in range(args.copies):
        testCases = UnitTestCommon.loadTestCases(config, testFiles, bsaRootDir, 'ufora')
        if filterActions:
            testCases = applyFilterActions(filterActions, testCases)

        testCasesToRun += testCases

    if testFilter is not None:
        testCasesToRun = testFilter(testCasesToRun)

    if args.list:
        for test in testCasesToRun:
            print test.id()

        os._exit(0)

    if args.random:
        import random
        random.shuffle(testCasesToRun)

    if args.pythreadcheck:
        results = {}
        for test in testCasesToRun:
            results[test] = runPyTestSuite(config, None, unittest.TestSuite([test]), testArgs)

        return True in results.values()
    else:
        testFiles = '.'
        return runPyTestSuite(config, None, testCasesToRun, testArgs)

def startCoverageCollectionIfEnabled():
    if CodeCoverage.is_enabled():
        return CodeCoverage.start_collection()

def stopCoverageCollectionIfEnabled(cov):
    if cov is not None:
        CodeCoverage.stop_collection(cov)

def runNodeTests():
    exitCode = subprocess.call(
            "mocha --compilers coffee:coffee-script ufora/web/relay/server/unitTests/*",
            shell=True
            )
    return exitCode == 0

def executeTests(args):
    anyFailed = False

    if args.profile is not None:
        ufora.native.TCMalloc.cpuProfilerStart(args.profile)

    #TODO FIX
    if not args.list:
        print "UFORA root is " + ufora.rootPythonPath
        print "Test arguments: ", args
        print
        print

    if args.py or args.lang or args.native or args.localperf:
        FORA.initialize()

    if args.native and not args.list:
        print "Running C++ unit tests:"
        t0 = time.time()

        #see if native args had an optinal filter specified
        native_args = []
        if args.native is not True:
            native_args.append("--run_test=" + args.native)

        if ufora.native.Tests.test( (["--log_level=test_suite"] if args.testHarnessVerbose else []) + native_args ):
            anyFailed = True

        print "took ", time.time() - t0
        print "\n\n"


    if args.py:
        filter = None

        if args.modpair is not None:
            def testFilterFunc(tests):
                result = []
                for t in tests:
                    hashval = hexToInt(hashlib.sha1(repr(t)).hexdigest())
                    if hashval % args.modpair[1] == args.modpair[0]:
                        result.append(t)
                return result
            filter = testFilterFunc

        if not args.list:
            print "Running python unit tests."
            print "nose version: ", nose.__version__
            print time.ctime(time.time())

        if runPythonUnitTests(args, filter):
            anyFailed = True

        print "\n\n\n"

    if args.localperf:
        print "Running FORA local performance unit tests:"
        if LocalPerfTest.test(args.list, makeSemanticsTestFilter(args)):
            anyFailed = True
        print "\n\n\n"

    if args.lang:
        print "Running FORA language semantics unit tests:"
        if FORASemanticsTest.test(args.testHarnessVerbose, makeSemanticsTestFilter(args)):
            anyFailed = True
        print "\n\n\n"

    if args.multibox:
        print "Running multibox tests"
        testRunner = MultiMachineTestRunner.createTestRunner(
            testDir=args.scriptPath or 'test_scripts/multibox'
            )
        if not testRunner.run():
            anyFailed = True
        print "\n\n\n"

    if args.scripts:
        print "Running script unit tests:"
        scriptRunner = TestScriptRunner(testRoot= args.scriptPath or "test_scripts", defaultTimeout=args.timeout[0])
        if CodeCoverage.is_enabled():
            print 'With code coverage'
            if not scriptRunner.runWithCodeCoverage():
                anyFailed = True
        elif not scriptRunner.run():
            anyFailed = True
        print "\n\n\n"

    if args.node:
        print "Running node.js tests:"
        anyFailed = not runNodeTests() or anyFailed

    if args.browser:
        print "Running browser end-to-end test"
        browserRunner = TestScriptRunner(testRoot='ufora/web/relay/test/e2e')
        if not browserRunner.run():
            anyFailed = True
        print "\n\n\n"


    if anyFailed:
        print "Some unit tests failed!"
    else:
        print "All tests passed."


    import ufora.native.Tests as Tests
    Tests.gcov_flush()

    if args.profile is not None:
        ufora.native.TCMalloc.cpuProfilerStop()

    if anyFailed:
        return 1
    return 0


def noTestsSelected(args):
    return not (args.lang or args.native or args.scripts or args.py or \
                    args.node or args.browser or args.localperf or args.multibox)

def main(args):
    if noTestsSelected(args):
        args.lang,args.native,args.py,args.scripts,args.node = True,True,True,True,False

    def runTests():
        if args.timeout is not None:
            UnitTestCommon.startTimeoutThread(args.timeout[0])

        try:
            return executeTests(args)
        except:
            import traceback
            logging.error("executeTests() threw an exception: \n%s", traceback.format_exc())
            return 1

    if args.repeat:
        while True:
            runTests()
    else:
        return runTests()

if __name__ == "__main__":
    #parse args, return zero and exit if help string was printed
    parser = UnitTestArgumentParser()
    generalArgumentsGroup = parser.add_argument_group(
        title="General Arguments",
        description="Arguments that affect the system as a whole")

    Setup.addDefaultArguments(generalArgumentsGroup)
    Mainline.addNoseVerbosityArgument(parser)
    Mainline.UserFacingMainline(main, sys.argv, [], parser=parser)

