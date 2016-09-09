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

class TestHarnessCorrectnessTest(unittest.TestCase):
    @staticmethod
    def shouldSkip():
        return "TEST_HARNESS_TESTS" not in os.environ

    def test_unittestAssertion(self):
        if self.shouldSkip():
            return
        self.assertTrue(False, "unittest asserts should fail tests")

    def test_raisesException(self):
        if self.shouldSkip():
            return
        raise Exception("raised exceptions should fail tests")

    def test_pythonAssertion(self):
        if self.shouldSkip():
            return
        assert False, "assertions should fail tests"

