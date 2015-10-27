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

import os
import logging
import traceback
import fcntl
import re
import unittest
import sys
import ufora.config.Mainline as Mainline
import ufora.native.Logging as NativeLogging



levels = ["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]


def matchLog(level, text):
    match = re.match('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} %s LoggingConfig.py.cxx:\d{1,5}\ *: (.*)\n$' % level, text)
    if match and len(match.groups()):
        return match.groups()[0]
    return None

class LoggingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readFd,  w = os.pipe()
        flags = fcntl.fcntl(cls.readFd, fcntl.F_GETFL, 0)
        fcntl.fcntl(cls.readFd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        os.dup2(w, 2)


    @classmethod
    def tearDownClass(cls):
        line = cls.read(1024)
        while line != '':
            sys.stdout.write(line)
            line = cls.read(1024)

    @classmethod
    def read(cls, bytes):
        try:
            return os.read(cls.readFd, bytes)
        except:
            return ''


    def flushToStdout(self):
        toWrite = self.read(1024)
        while toWrite != '':
            sys.stdout.write(toWrite)
            toWrite = self.read(1024)

    def setUp(self):
        self.flushToStdout()
    def tearDown(self):
        self.flushToStdout()

    def tryLogging(self, message, expected):
        for level in levels:
            NativeLogging.log(getattr(logging, level), message)
            output = self.read(1024)
            self.assertEqual(matchLog(level, output), expected[level])



    def test_should_log(self):
        testMessage = "this is a test"
        for level in levels:
            loggingLevel = getattr(logging, level)
            NativeLogging.setLogLevel(loggingLevel)
            try:
                self.tryLogging(
                    testMessage,
                    {
                        "DEBUG" : testMessage if loggingLevel <= logging.DEBUG else None,
                        "INFO" : testMessage if loggingLevel <= logging.INFO else None,
                        "WARN" : testMessage if loggingLevel <= logging.WARN else None,
                        "ERROR" : testMessage if loggingLevel <= logging.ERROR else None,
                        "CRITICAL" : testMessage if loggingLevel <= logging.CRITICAL else None
                    }
                )
            except:
                traceback.print_exc()
                raise
                pass


    def test_logging_basic(self):
        for level in levels:
            loggingLevel = getattr(logging, level)
            NativeLogging.setLogLevel(loggingLevel)
            for testLevel in levels:
                self.assertEqual(
                    NativeLogging.shouldLog(getattr(logging, testLevel)),
                    True if loggingLevel <= getattr(logging, testLevel) else False)







if __name__ == '__main__':
    Mainline.UnitTestMainline([], disableLogCapture=True)



