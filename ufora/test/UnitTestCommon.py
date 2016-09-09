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

import sys
import unittest
import os
import re
import traceback
import threading
import time
import nose
import nose.config
import nose.loader
import nose.plugins.manager
import nose.plugins.xunit
import logging
import ufora.native
import ufora.util.DirectoryScope as DirectoryScope


def sortedBy(elts, sortFun):
    return [x[1] for x in sorted([(sortFun(y),y) for y in elts])]

def findTestFiles(rootDir, testRegex):
    logging.info('finding files from root %s', rootDir)
    testPattern = re.compile(testRegex)
    testFiles = []
    for directory, subdirectories, files in os.walk(rootDir):
        testFiles += [os.path.join(directory, f) for f in files if testPattern.match(f) is not None]

    return testFiles



def flattenToTestCases(suite):
    if isinstance(suite, list) or isinstance(suite, unittest.TestSuite):
        return sum([flattenToTestCases(x) for x in suite], [])
    return [suite]




def fileNameToModuleName(fileName, rootDir, rootModule):
    tr = (
        fileName
            .replace('.py', '')
            .replace(rootDir, rootModule)
            .replace(os.sep, '.')
            )
    if tr.startswith('.'):
        return tr[1:]
    return tr


def loadTestModules(testFiles, rootDir, rootModule):
    modules = set()
    for f in testFiles:
        try:
            with DirectoryScope.DirectoryScope(os.path.split(f)[0]):
                moduleName  = fileNameToModuleName(f, rootDir, rootModule)
                logging.info('importing module %s', moduleName)
                __import__(moduleName)
                modules.add(sys.modules[moduleName])
        except ImportError:
            logging.error("Failed to load test module: %s", moduleName)
            traceback.print_exc()
            raise

    return modules

def testCaseHasAttribute(testCase, attributeName):
    """Determine whether a unittest.TestCase has a given attribute."""
    if hasattr(getattr(testCase, testCase._testMethodName), attributeName):
        return True
    if hasattr(testCase.__class__, attributeName):
        return True
    return False

def extractTestCases(suites):
    testCases = flattenToTestCases(suites)
    #make sure the tests are sorted in a sensible way.
    sortedTestCases = sortedBy(testCases, lambda x: x.id())

    return [x for x in sortedTestCases if not testCaseHasAttribute(x, 'disabled')]

def loadTestsFromModules(config, modules):
    loader = nose.loader.TestLoader(config = config)
    allSuites = []
    for module in modules:
        cases = loader.loadTestsFromModule(module)
        allSuites.append(cases)

    return allSuites


def loadTestCases(config, testFiles, rootDir, rootModule):
    modules = sortedBy(loadTestModules(testFiles, rootDir, rootModule), lambda module: module.__name__)
    allSuites = loadTestsFromModules(config, modules)
    return extractTestCases(allSuites)

def startTimeoutThread(timeout):
    '''
    Start a thread which will eventually kill the process if the tests aren't finished
    after the timeout
    '''
    assert timeout is not None
    def killer():
        time.sleep(timeout)
        print >> sys.stderr
        print >> sys.stderr, ' *** Test failed to finish in %s seconds, aborting *** ' % timeout
        ufora.native.Tests.forceStackdump()

    t = threading.Thread(target=killer)
    t.daemon = True
    t.start()





