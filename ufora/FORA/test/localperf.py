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
import os
import logging
import traceback

import ufora.FORA.test as FORATestModule
import ufora.FORA.python.FORA as FORA
import ufora.FORA.test.PerfTestBase as PerfTestBase
import ufora.config.Setup as Setup

from ufora.FORA.python.ForaValue import FORAValue, FORATuple

def test(listOnly = False, testFilter = None):
    return LocalPerf().test(listOnly, testFilter)

class LocalPerf(PerfTestBase.PerfTestBase):
    def test(self, listOnly = False, testFilter = None):
        perfTestCases, metaDataForPerfTests = self.getPerfTestsInLangTests()

        numPassed = 0
        numFailed = 0
        failures = []

        t0 = time.time()
        for filename, perfTestCasesInModule in perfTestCases.iteritems():
            for testCase in perfTestCasesInModule:
                if testFilter is None or testFilter(filename, testCase):

                    if listOnly:
                        logging.info("%s:%s" % (filename, testCase))
                        print "%s:%s" % (filename, testCase)
                        continue

                    try:
                        logging.info("measuring perf for %s:%s" % (filename, testCase))
                        print "measuring perf for %s:%s" % (filename, testCase)

                        filenameAsModuleName = os.path.splitext(filename)[0]

                        res = self.validatePerfForModuleMember(
                            "LangTestPerf." + filenameAsModuleName + "." + testCase,
                            filename, testCase,
                            metaDataForPerfTests[(filename, testCase)]
                            )
                        numPassed += 1
                    except AssertionError as e:
                        failures.append(
                            (filename + ":" + testCase, e)
                            )
                        numFailed += 1

        if listOnly:
            return 0

        print "numPassed = %s, numFailed = %s, failures = %s\nbaseTiming = %s" % (
            numPassed, numFailed, failures, self.baseTiming),
        print " in ", time.time() - t0

        time.sleep(0.5)

        if numFailed > 0:
            return 1
        return 0

    def isPerfTestCase(self, foraMemberMetadata):
        Symbol_perf = FORAValue.makeSymbol("perf")
        if foraMemberMetadata.outer == Symbol_perf:
            return True
        if isinstance(foraMemberMetadata.outer, tuple) or \
           isinstance(foraMemberMetadata.outer, FORATuple):
            if Symbol_perf in foraMemberMetadata.outer:
                return True

        return False

    def getPerfTestsInLangTests(self):
        perfTestCases = dict()
        metadataForPerfTestCases = dict()

        testPath = os.path.split(FORATestModule.__file__)[0]
        foraFiles = [x for x in os.listdir(testPath) if x.endswith(".fora")]

        for filename in foraFiles:
            foraModule = FORA.importModule(os.path.join(testPath, filename))
            moduleMembersAndMetadataDict = FORA.objectMembers(foraModule)

            for memberName, memberMetadata in moduleMembersAndMetadataDict.iteritems():
                if self.isPerfTestCase(memberMetadata):
                    if filename not in perfTestCases:
                        perfTestCases[filename] = set()
                    perfTestCases[filename].add(memberName)
                    metadataForPerfTestCases[(filename, memberName)] = memberMetadata.outer

        return perfTestCases, metadataForPerfTestCases

if __name__ == "__main__":
    setup = Setup.defaultSetup()
    with Setup.PushSetup(setup):
        Setup.config().configureLoggingForUserProgram()

        FORA.initialize()

        langfilter = None
        listOnly = False

        try:
            result = test()
        except:
            logging.critical(traceback.format_exc())
            result = 1



