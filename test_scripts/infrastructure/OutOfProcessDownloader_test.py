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
import ufora.util.OutOfProcessDownloader as OutOfProcessDownloader
import ufora.util.OutOfProcessDownloaderTestCases as OutOfProcessDownloaderTestCases
import ufora.config.Mainline as Mainline
import ufora.distributed.util.common as common
import Queue
import time
import logging
import os

#we have to run these tests from a separate process. If we run them in the main harness,
#then sometimes there is a lot of memory pressure and "fork" fails. This is really an artifact
#of our test framework, so running these tests in a clean environment makes more sense.
class OutOfProcessDownloaderTest(unittest.TestCase, OutOfProcessDownloaderTestCases.OutOfProcessDownloaderTestCases):
    pass


if __name__ == '__main__':
    Mainline.UnitTestMainline([])

