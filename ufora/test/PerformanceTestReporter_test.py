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
import os
import tempfile
import ufora.test.PerformanceTestReporter as PerformanceTestReporter

class SetEnv(object):
    def __init__(self, env, target):
        self.env = env
        self.target = target
        self.old = None

    def __enter__(self):
        self.old = os.getenv(self.env)
        if self.target is None:
            if self.old is not None:
                del os.environ[self.env]
        else:
            os.environ[self.env] = self.target

    def __exit__(self, *args, **kwds):
        if self.old is None:
            if self.target is not None:
                del os.environ[self.env]
        else:
            if self.old is not None:
                os.environ[self.env] = self.old



class TestPerformanceTestReporter(unittest.TestCase):
    def test_knows_is_reporting(self):
        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                None):
            self.assertFalse(PerformanceTestReporter.isCurrentlyTesting())

        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                "./testResults.json"):
            self.assertTrue(PerformanceTestReporter.isCurrentlyTesting())

    def throws_if_not_reporting(self):
        with self.assertRaises(Exception):
            PerformanceTestReporter.recordTest("test1",10.0,None)

    def test_reporting_to_file(self):
        tempDir = tempfile.mkdtemp()
        tempFile = os.path.join(tempDir, "data.json")

        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                tempFile
                ):
            PerformanceTestReporter.recordTest("test1.result", 10.0, {"some":"metadata"})
            PerformanceTestReporter.recordTest("test1.result", None, {"some":"metadata"})

        testData = PerformanceTestReporter.loadTestsFromFile(tempFile)

        self.assertEqual(testData,
            [{"name":"test1.result", "time":10.0, "metadata": {"some":"metadata"}},
             {"name":"test1.result", "time":None, "metadata": {"some":"metadata"}}
             ])

    def test_throughputDoesNotFailOnTimeoutIfSomePassed(self):
        tempDir = tempfile.mkdtemp()
        tempFile = os.path.join(tempDir, "data.json")

        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                tempFile
                ):
            def testFunOfN(n):
                if n < 10:
                    pass
                else:
                    raise PerformanceTestReporter.TimedOutException("timed out!!")
            PerformanceTestReporter.testThroughput(
                "test1", testFunOfN = testFunOfN)
            
        testData = PerformanceTestReporter.loadTestsFromFile(tempFile)

        self.assertEqual(len(testData), 1)

    def test_throughputThrowsIfNonePassed(self):
        tempDir = tempfile.mkdtemp()
        tempFile = os.path.join(tempDir, "data.json")

        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                tempFile
                ):
            def testFunOfN(n):
                raise PerformanceTestReporter.TimedOutException("timed out!!")

            with self.assertRaises(AssertionError):
                PerformanceTestReporter.testThroughput(
                    "test1", testFunOfN = testFunOfN)

    def test_cant_report_nonsensical_timing(self):
        tempDir = tempfile.mkdtemp()
        tempFile = os.path.join(tempDir, "data.json")

        with SetEnv(
                PerformanceTestReporter.TEST_DATA_LOCATION_ENVIRONMENT_VARIABLE, 
                tempFile
                ):
            with self.assertRaises(Exception):
                PerformanceTestReporter.recordTest("test1","not a float",None)

