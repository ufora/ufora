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

"""
PerformanceTestReporter

Allows test programs to report back performance data to a test-script runner. Test data is passed
in test files. The location of the files is passed to client programs using environment variables.
"""

import os
import json
import time
import inspect

TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE = "UFORA_PERFORMANCE_TEST_RESULTS_FILE"

class TimedOutException(Exception):
    pass

def isCurrentlyTesting():
    return os.getenv(TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE) is not None

def recordTest(testName, elapsedTime, metadata, **kwargs):
    if not (isinstance(elapsedTime, float) or elapsedTime is None):
        raise UserWarning(
            "We may only record a float, or None (in case of failure) for elapsed time"
            )

    if not isCurrentlyTesting():
        raise UserWarning(
            "We are not currently testing, so we can't record test results. "
            "Set the environment variable " + TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE +
            " to point to a valid path.")

    targetPath = os.getenv(TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE)

    perfLogEntry = {
        "name": str(testName),
        "time": elapsedTime if isinstance(elapsedTime, float) else None,
        "metadata": metadata
        }
    perfLogEntry.update(kwargs)

    if targetPath == '-':
        print "%2.2f  --  %s" % (elapsedTime, testName)
    else:
        with open(targetPath, "ab+") as f:
            f.write(json.dumps(perfLogEntry) + "\n")

def recordThroughputTest(testName, runtime, n, baseMultiplier, metadata):
    recordTest(testName,
               runtime / n * baseMultiplier,
               metadata,
               n=n,
               baseMultiplier=baseMultiplier,
               actualTime=runtime)

def testThroughput(testName,
                   testFunOfN,
                   setupFunOfN=None,
                   transformOfN=None,
                   metadata=None,
                   maxNToSearch=1000000,
                   baseMultiplier=1,
                   timeoutInSec=30.0):
    counter = 0
    unitOfWork = counter
    unitsOfWorkCompleted = 0
    runtime = None

    timeUsed = 0

    while timeUsed < timeoutInSec and counter <= maxNToSearch:
        try:
            counter += 1

            unitOfWork = counter
            if transformOfN is not None:
                unitOfWork = transformOfN(counter)

            if setupFunOfN is not None:
                setupFunOfN(unitOfWork)

            t0 = time.time()
            testFunOfN(unitOfWork)
            runtime = time.time() - t0

            if timeUsed < timeoutInSec:
                unitsOfWorkCompleted += unitOfWork

            timeUsed += runtime

        except TimedOutException:
            break

    # we had at least one passing result before timing out
    assert runtime is not None
    assert unitsOfWorkCompleted > 0

    if isCurrentlyTesting():
        recordThroughputTest(testName, timeUsed, unitsOfWorkCompleted, baseMultiplier, metadata)

def loadTestsFromFile(testFileName):
    with open(testFileName, "rb") as f:
        return [json.loads(x) for x in f.readlines()]

def PerfTest(testName):
    """Decorate a unit-test so that it records performance in the global test database"""
    def decorator(f):
        meta = {
            'file': "/".join(inspect.getmodule(f).__name__.split(".")) + ".py",
            'line': inspect.getsourcelines(f)[1]
            }

        def innerTestFun(self):
            t0 = time.time()

            try:
                result = f(self)
            except:
                if isCurrentlyTesting():
                    recordTest(testName, None, meta)
                raise

            if isCurrentlyTesting():
                recordTest(testName, time.time() - t0, meta)

            return result

        innerTestFun.__name__ = f.__name__
        return innerTestFun

    return decorator

def getCurrentStackframeFileAndLine(framesAbove):
    curStack = inspect.currentframe()
    above = inspect.getouterframes(curStack)
    twoAbove = above[framesAbove][0]

    return {
        'file': "/".join(inspect.getmodule(twoAbove).__name__.split(".")) + ".py",
        'line': inspect.getsourcelines(twoAbove)[1]
        }

