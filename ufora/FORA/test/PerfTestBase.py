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

import ufora.FORA.test.ValidatePerf as ValidatePerf
import ufora.core.SubprocessRunner as SubprocessRunner
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
from ufora.FORA.python.ForaValue import FORATuple
from ufora.FORA.python.ForaValue import FORAValue

import time
import sys
import logging

_baseTiming = None

Symbol_callResult = FORAValue.makeSymbol("callResult")

def computeBaseTiming():
    times = []

    for ix in range(101):
        t0 = time.time()
        x = 0
        while x < 1000000:
            x=x+1
        times.append(time.time() - t0)

    import logging
    logging.info("base timing: " + str(min(times)))
    return min(times)

class PerfTestBase(object):
    @property
    def baseTiming(self):
        global _baseTiming
        if _baseTiming is None:
            _baseTiming = computeBaseTiming()
        return _baseTiming

    def validateTimingsForSubprocessCall(
                self, 
                testName,
                subprocessArgs, 
                meta,
                timeout = 600.0
                ):
        resultCode, out, err = SubprocessRunner.callAndReturnResultAndOutput(
            subprocessArgs,
            timeout = timeout
            )


        if resultCode != 0:
            meta.update({"failure": "subprocess call returned error"})

            if PerformanceTestReporter.isCurrentlyTesting():
                PerformanceTestReporter.recordTest(
                    testName,
                    None,
                    meta
                    )

        assert resultCode == 0, err

        logging.info("Actual time was %s for %s", out[0], subprocessArgs)

        measuredTiming = float(out[0]) / self.baseTiming

        if PerformanceTestReporter.isCurrentlyTesting():
            PerformanceTestReporter.recordTest(
                "fora_lang." + testName,
                float(out[0]),
                meta
                )

    def shouldCallResult(self, metadataForMember):
        if isinstance(metadataForMember, tuple) or \
           isinstance(metadataForMember, FORATuple):
            if Symbol_callResult in metadataForMember:
                return True

        return False

    def validatePerfForModuleMember(self, testName, moduleFileName, testCaseMemberName, 
                                    metadataForMember):
        subprocessArgs = [sys.executable, ValidatePerf.__file__, moduleFileName, \
                              testCaseMemberName, "moduleMember"]

        if self.shouldCallResult(metadataForMember):
            subprocessArgs.append("callResult")

        self.validateTimingsForSubprocessCall(
            testName,
            subprocessArgs, 
            {'file': "ufora/FORA/test/" + moduleFileName}
            )

    def validatePerfForExpression(self, testName, foraExpr, callResult = False):
        subprocessArgs = \
            [sys.executable, ValidatePerf.__file__, foraExpr];

        if callResult:
            subprocessArgs.append("callResult")

        self.validateTimingsForSubprocessCall(
            testName,
            subprocessArgs, 
            PerformanceTestReporter.getCurrentStackframeFileAndLine(framesAbove=2)
            )

