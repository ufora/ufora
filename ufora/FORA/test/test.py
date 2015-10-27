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
command-line interface to test the FORA runtime semantics

test.py 'module1.fora' 'module2.fora' ...

The tester takes a list of FORA module files on the command line.

members marked with metadata `test, or with tuple metadata (holding `test) are considered test cases.
"""

# TODO BUG anybody: when a module doesn't parse, test.py failes entirely rather than noting that the object itself fails
# TODO BUG anybody: The module parser has trouble finding other modules when test.py is not in the same directory as the .fora file being tested

#In order to control logging behavior, ufora.Native.Logging has to be
#triggered before FORA is imported. So, we set FORA to None,
#and all entrypoints are responsible for setting it when importing

import ufora.FORA.python.FORA as FORA
import ufora.native.FORA as ForaNative
from ufora.FORA.python.ForaValue import FORAValue, FORAException
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.FORA.python.ParseException as ParseException
import time
import os
import sys
import traceback
import logging
import ufora.config.Setup as Setup

testSymbol = ForaNative.makeSymbol("test")

def isTestCase(foraMemberMetadata):
    """
    given a module metadata `foraMemberMetadata`, 
    return true if the member is a test case, or false otherwise. 

    as described above, a test case is one in which the metadata is either `test, or
    is a tuple containing the value `test (among possibly other things)
    """
    if foraMemberMetadata is None:
        return False

    metaIVC = FORA.extractImplValContainer(foraMemberMetadata).getTupleMember("outer")

    if metaIVC is None:
        return False

    if metaIVC == testSymbol:
        return True

    if metaIVC.isTuple():
        for ix in range(len(metaIVC)):
            if metaIVC[ix] == testSymbol:
                return True

    return False

def extractModuleTestNames(foraModule):
    """
    get a a list of the module members which are test cases
    """
    
    moduleMembersAndMetadataDict = FORA.objectMembers(foraModule)

    tr = []
    
    for membername, memberMeta in moduleMembersAndMetadataDict.iteritems():
        if isTestCase(memberMeta):
            tr.append(membername)

    return tr

def sanitizeErrString(errString):
    """pack the error string into a single line of a few characters. include the beginning and end"""
    errString = errString.replace("\n", " ").replace("\t", " ")
    
    if len(errString) > 500:
        errString = errString[:250] + " ... " + errString[-250:]
    return errString
    
def printTestResults(moduleName, testName, testResultWithTimes, printSuccesses = False):
    failct = 0
    passct = 0

    result, timeElapsed = testResultWithTimes

    if result is not True:
        failct += 1
            
        print moduleName, ": ", testName,

        print "FAIL ", testName, ":",
        if isinstance(result, FORAException):
            print "throw", sanitizeErrString(str(result.foraVal))
        else:
            print result,
        print " is not True "
            
    else:
        passct += 1
        if printSuccesses:
            print moduleName, testName, ": SUCC in %2.4f" % timeElapsed
            
    return (passct, failct)

def executeFORATest(foraModule, testname, printSuccesses = False):
    try:
        if printSuccesses:
            print "running ", testname
        
        return getattr(foraModule, testname)


    except FORAException as e:
        return e
    
def testModuleStr(modulePath, printSuccesses, delay, testFilter):
    """parse text in moduleText into a FORA module and execute tests within"""
    try:
        foraModule = FORA.importModule(modulePath)
    except ParseException.ParseException as parseException:
        print "Failed to import module %s: %s" % (modulePath, parseException)
        return (0, 1)

    moduleName = os.path.split(modulePath)[-1]
    testNames = extractModuleTestNames(foraModule)

    allPassed = 0
    allFailed = 0

    for testName in testNames:
        if testFilter is None or testFilter(modulePath, testName):
            time.sleep(delay)

            t0 = time.time()
            testResults = []

            testResultWithTimes = (executeFORATest(foraModule, testName, printSuccesses), time.time() - t0)

            passed, failed = printTestResults(
                moduleName,
                testName,
                testResultWithTimes,
                printSuccesses
                )

            allPassed += passed
            allFailed += failed

    return (allPassed, allFailed)

def main(argv = None):     
    if argv is None:
        argv = sys.argv

    if '--logging' in argv:
        import logging
        Setup.config().setLoggingLevel("debug")

    Setup.config().configureLoggingForUserProgram()

    allPassed = 0
    allFailed = 0
    
    t0 = time.time()
    
    repeat = '-repeat' in argv
    printSuccesses = '-v' in argv
    
    delay = 0.0
    if '-d' in argv:
        delay = .05
    
    done = False
    while not done:
        for filename in [x for x in argv[1:] if not x.startswith("-") and x not in ('0','1')]:
            passed, failed = testModuleStr(filename, printSuccesses, delay, None)
            allPassed += passed
            allFailed += failed
            print filename, ": ", passed, " passed, ", failed, " failed."
        if not repeat:
            done = True

    print "ALL TESTS EXECUTED. %d passed, %d failed." % (allPassed, allFailed),
    print " in ", time.time() - t0
    
    time.sleep(.5)
    
    if allFailed > 0:
        return 1
    return 0

def test(verbose = False, testFilter=None):
    """use all .fora files in this directory to generate a single unit test.
    
    returns 1 on failure, 0 on success

    testFilter - a function from modulename and testname to a bool indicating whether to test
    """
    numPassed = 0
    numFailed = 0
    
    curdir = os.path.split(__file__)[0]
    t0 = time.time()
    
    for f in sorted(os.listdir(curdir)):
        if f.endswith(".fora"):
            passed, failed = testModuleStr(os.path.join(curdir, f), verbose, 0.0, testFilter)
            numPassed += passed
            numFailed += failed
            
    print "FORA SEMANTIC TESTS EXECUTED. %d passed, %d failed." % (numPassed, numFailed),
    print " in ", time.time() - t0
    
    time.sleep(.5)
    
    if numFailed > 0:
        return 1
    return 0
    
if __name__ == "__main__":
    setup = Setup.defaultSetup()
    with Setup.PushSetup(setup):
        Setup.config().configureLoggingForUserProgram()

        FORA.initialize()
        
        try:
            result = main()
        except:
            logging.critical(traceback.format_exc())
            result = 1

        sys.exit(result)

