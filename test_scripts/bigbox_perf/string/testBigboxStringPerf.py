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

import unittest
import time
import ufora.FORA.python.FORA as FORA
import ufora.cumulus.test.InMemoryCumulusSimulation as InMemoryCumulusSimulation
import ufora.distributed.S3.InMemoryS3Interface as InMemoryS3Interface
import ufora.native.CallbackScheduler as CallbackScheduler
import ufora.test.PerformanceTestReporter as PerformanceTestReporter
import ufora.FORA.python.Runtime as Runtime

callbackScheduler = CallbackScheduler.singletonForTesting()

class BigboxStringPerformanceTest(unittest.TestCase):
    def computeUsingSeveralWorkers(self, *args, **kwds):
        return InMemoryCumulusSimulation.computeUsingSeveralWorkers(*args, **kwds)

    def stringCreationAndSumTest(self, totalStrings, workers, threadsPerWorker, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """Vector.range(%s, String).sum(size)""" % totalStrings

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                workers,
                timeout = 240,
                memoryLimitMb = 55 * 1024 / workers,
                threadCount = threadsPerWorker,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_createData_strings_4threads_100M(self):
        self.stringCreationAndSumTest(100000000, 1, 4, "python.BigBox.StringCreation.100M.4Threads")

    def test_createData_strings_30threads_100M(self):
        self.stringCreationAndSumTest(100000000, 1, 30, "python.BigBox.StringCreation.100M.30Threads")

    def test_createData_strings_4threads(self):
        self.stringCreationAndSumTest(1000000000, 1, 4, "python.BigBox.StringCreation.1B.4Threads")

    def test_createData_strings_30threads(self):
        self.stringCreationAndSumTest(1000000000, 1, 30, "python.BigBox.StringCreation.1B.30Threads")

    def stringToDatetimeParsingTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let s = ["2013-01-01 15:18:10"][0];

            let doALoop = fun(x) {
                let res = 0
                for ix in sequence(x) {
                    res = res + DateTime(s).year
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(1000000 + _)}
            """.replace("__thread_count__", str(threads))

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024 / workers,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_parseStringToDate_1(self):
        self.stringToDatetimeParsingTest(1, "python.BigBox.StringToDateParse.01Threads")

    def test_parseStringToDate_2(self):
        self.stringToDatetimeParsingTest(2, "python.BigBox.StringToDateParse.02Threads")

    def test_parseStringToDate_5(self):
        self.stringToDatetimeParsingTest(5, "python.BigBox.StringToDateParse.05Threads")

    def test_parseStringToDate_10(self):
        self.stringToDatetimeParsingTest(10, "python.BigBox.StringToDateParse.10Threads")

    def test_parseStringToDate_30(self):
        self.stringToDatetimeParsingTest(30, "python.BigBox.StringToDateParse.30Threads")

    def stringToDatetimeParsingTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let s = ["2013-01-01 15:18:10"][0];

            let doALoop = fun(x) {
                let res = 0
                for ix in sequence(x) {
                    res = res + DateTime(s).year
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(4000000 + _)}
            """.replace("__thread_count__", str(threads))

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_parseStringToDate_1(self):
        self.stringToDatetimeParsingTest(1, "python.BigBox.StringToDateParse.01Threads")

    def test_parseStringToDate_2(self):
        self.stringToDatetimeParsingTest(2, "python.BigBox.StringToDateParse.02Threads")

    def test_parseStringToDate_5(self):
        self.stringToDatetimeParsingTest(5, "python.BigBox.StringToDateParse.05Threads")

    def test_parseStringToDate_10(self):
        self.stringToDatetimeParsingTest(10, "python.BigBox.StringToDateParse.10Threads")

    def test_parseStringToDate_30(self):
        self.stringToDatetimeParsingTest(30, "python.BigBox.StringToDateParse.30Threads")

    def stringToFloat64ParsingTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let doALoop = fun(x) {
                //pass 's' through a vector so that the compiler can't tell what it is
                let s = ["2013.0"][0];

                let res = 0
                for ix in sequence(x) {
                    res = res + Float64(s) + ix
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(20000000 + _)}
            """.replace("__thread_count__", str(threads))

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()


    def stringToInt64ParsingTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let doALoop = fun(x) {
                //pass 's' through a vector so that the compiler can't tell what it is
                let s = ["2013"][0];

                let res = 0
                for ix in sequence(x) {
                    if (ix == 0)
                        s = s + String(ix)

                    res = res + Int64(s) + ix
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(20000000 + _)}
            """.replace("__thread_count__", str(threads))

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_parseStringToInt64_1(self):
        self.stringToInt64ParsingTest(1, "python.BigBox.StringToInt64Parse.01Threads")

    def test_parseStringToInt64_2(self):
        self.stringToInt64ParsingTest(2, "python.BigBox.StringToInt64Parse.02Threads")

    def test_parseStringToInt64_5(self):
        self.stringToInt64ParsingTest(5, "python.BigBox.StringToInt64Parse.05Threads")

    def test_parseStringToInt64_10(self):
        self.stringToInt64ParsingTest(10, "python.BigBox.StringToInt64Parse.10Threads")

    def test_parseStringToInt64_30(self):
        self.stringToInt64ParsingTest(30, "python.BigBox.StringToInt64Parse.30Threads")

    def test_parseStringToFloat64_1(self):
        self.stringToFloat64ParsingTest(1, "python.BigBox.StringToFloat64Parse.01Threads")

    def test_parseStringToFloat64_2(self):
        self.stringToFloat64ParsingTest(2, "python.BigBox.StringToFloat64Parse.02Threads")

    def test_parseStringToFloat64_5(self):
        self.stringToFloat64ParsingTest(5, "python.BigBox.StringToFloat64Parse.05Threads")

    def test_parseStringToFloat64_10(self):
        self.stringToFloat64ParsingTest(10, "python.BigBox.StringToFloat64Parse.10Threads")

    def test_parseStringToFloat64_30(self):
        self.stringToFloat64ParsingTest(30, "python.BigBox.StringToFloat64Parse.30Threads")

    def stringFromFloat64ParsingTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()

        #we wish we could actually test that we achieve saturation here but we can't yet.
        text = """
            let s = [2013.0][0];

            let doALoop = fun(x) {
                let res = 0
                for ix in sequence(x) {
                    res = res + size(String(s))
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(1000000 + _)}
            """.replace("__thread_count__", str(threads))

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_parseStringFromFloat64_1(self):
        self.stringFromFloat64ParsingTest(1, "python.BigBox.StringFromFloat64Parse.01Threads")

    def test_parseStringFromFloat64_2(self):
        self.stringFromFloat64ParsingTest(2, "python.BigBox.StringFromFloat64Parse.02Threads")

    def test_parseStringFromFloat64_5(self):
        self.stringFromFloat64ParsingTest(5, "python.BigBox.StringFromFloat64Parse.05Threads")

    def test_parseStringFromFloat64_10(self):
        self.stringFromFloat64ParsingTest(10, "python.BigBox.StringFromFloat64Parse.10Threads")

    def test_parseStringFromFloat64_30(self):
        self.stringFromFloat64ParsingTest(30, "python.BigBox.StringFromFloat64Parse.30Threads")

    def loopScalabilityTestTest(self, threads, testName):
        s3 = InMemoryS3Interface.InMemoryS3InterfaceFactory()


        text = """
            let doALoop = fun(x) {
                let res = 0
                for ix in sequence(x) {
                    res = res + ix + 1
                    }
                res
                };

            Vector.range(__thread_count__) ~~ {doALoop(1000000000 + _)}
            """.replace("__thread_count__", str(threads))

        t0 = time.time()

        _, simulation = \
            self.computeUsingSeveralWorkers(
                "1+1",
                s3,
                1,
                timeout = 240,
                memoryLimitMb = 55 * 1024,
                threadCount = 30,
                returnSimulation = True,
                useInMemoryCache = False
                )

        try:
            t0 = time.time()
            result = simulation.compute(text, timeout=240)
            totalTimeToReturnResult = time.time() - t0

            PerformanceTestReporter.recordTest(testName, totalTimeToReturnResult, None)
        finally:
            simulation.teardown()

    def test_loopScalability_1(self):
        self.loopScalabilityTestTest(1, "python.BigBox.LoopScalabilityTest.01Threads")

    def test_loopScalability_2(self):
        self.loopScalabilityTestTest(2, "python.BigBox.LoopScalabilityTest.02Threads")

    def test_loopScalability_5(self):
        self.loopScalabilityTestTest(5, "python.BigBox.LoopScalabilityTest.05Threads")

    def test_loopScalability_10(self):
        self.loopScalabilityTestTest(10, "python.BigBox.LoopScalabilityTest.10Threads")

    def test_loopScalability_15(self):
        self.loopScalabilityTestTest(15, "python.BigBox.LoopScalabilityTest.15Threads")

    def test_loopScalability_30(self):
        self.loopScalabilityTestTest(30, "python.BigBox.LoopScalabilityTest.30Threads")

if __name__ == "__main__":
    import ufora.config.Mainline as Mainline
    Mainline.UnitTestMainline([FORA, Runtime])

