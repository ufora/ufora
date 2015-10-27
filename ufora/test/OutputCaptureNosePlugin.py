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
This plugin captures stdout during test execution. If the test fails
or raises an error, the captured output will be appended to the error
or failure output. It is enabled by default but can be disabled with
the options ``-s`` or ``--nocapture``.

:Options:
  ``--nocapture``
    Don't capture stdout (any stdout output will be printed immediately)

"""
import os
import sys
from nose.plugins.base import Plugin
from nose.util import ln
from StringIO import StringIO
import ufora.config.Config as Config
import ufora.native.Logging as NativeLogging
import time
import logging
import traceback

def setLoggingLevel(level):
    logging.getLogger().setLevel(level)
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)
    NativeLogging.setLogLevel(level)

def logAsInfo(*args):
    if len(args) == 1:
        print time.asctime(), " | ", args
    else:
        print time.asctime(), " | ", args[0] % args[1:]

class OutputCaptureNosePlugin(Plugin):
    """
    Output capture plugin. Enabled by default. Disable with ``-s`` or
    ``--nocapture``. This plugin captures stdout during test execution,
    appending any output captured to the error or failure output,
    should the test fail or raise an error.
    """
    enabled = True
    name = 'OutputCaptureNosePlugin'
    score = 16010

    def __init__(self):
        self.stdout = []
        self.stdoutFD = None
        self.stderrFD = None
        self.fname = None
        self.hadError=False
        self.outfile = None
        self.testStartTime = None
        self.nocaptureall = False

    def options(self, parser, env):
        """Register commandline options
        """
        parser.add_option(
            "--nocaptureall", action="store_true",
            default=False, dest="nocaptureall"
            )

    def configure(self, options, conf):
        """Configure plugin. Plugin is enabled by default.
        """
        self.conf = conf
        if options.nocaptureall:
            self.nocaptureall = True

    def afterTest(self, test):
        """Clear capture buffer.
        """
        if self.nocaptureall:
            if not self.hadError:
                logAsInfo("\tpassed in %s", time.time() - self.testStartTime)
            else:
                logAsInfo("\tfailed in %s seconds. See logs in %s", time.time() - self.testStartTime, self.fname)


        if self.stdoutFD is None:
            return

        setLoggingLevel(logging.ERROR)

        sys.stdout.flush()
        sys.stderr.flush()

        os.dup2(self.stdoutFD, 1)
        os.close(self.stdoutFD)

        os.dup2(self.stderrFD, 2)
        os.close(self.stderrFD)

        self.stdoutFD = None
        self.stderrFD = None

        self.outfile.flush()
        self.outfile.close()
        self.outfile = None

        if not self.hadError:
            try:
                os.remove(self.fname)
            except OSError:
                pass
            logAsInfo("\tpassed in %s", time.time() - self.testStartTime)
        else:
            #the test failed. Report the failure
            logAsInfo("\tfailed in %s seconds. See logs in %s", time.time() - self.testStartTime, self.fname)


    def begin(self):
        pass

    def beforeTest(self, test):
        """Flush capture buffer.
        """
        logAsInfo("Running test %s", test)

        self.testStartTime = time.time()

        if self.nocaptureall:
            self.hadError=False
            return

        sys.stdout.flush()
        sys.stderr.flush()

        self.stdoutFD = os.dup(1)
        self.stderrFD = os.dup(2)

        self.fname = "nose.%s.%s.log" % (test.id(), os.getpid())

        if os.getenv("UFORA_TEST_ERROR_OUTPUT_DIRECTORY", None) is not None:
            self.fname = os.path.join(os.getenv("UFORA_TEST_ERROR_OUTPUT_DIRECTORY"), self.fname)

        self.outfile = open(self.fname, "w")

        os.dup2(self.outfile.fileno(), 1)
        os.dup2(self.outfile.fileno(), 2)

        self.hadError=False

        setLoggingLevel(logging.INFO)

    def formatError(self, test, err):
        """Add captured output to error report.
        """
        self.hadError=True

        if self.nocaptureall:
            return err

        ec, ev, tb = err

        ev = self.addCaptureToErr(ev, tb)

        #print statements here show up in the logfile
        print "Test ", test, ' failed: '
        print ev

        self.failureReason = ev

        return (ec, ev, tb)

    def formatFailure(self, test, err):
        """Add captured output to failure report.
        """
        self.hadError=True
        return self.formatError(test, err)

    def addCaptureToErr(self, ev, tb):
        return ''.join([unicode(str(ev) + "\n")] + traceback.format_tb(tb) + ['\n>> output captured in %s <<' % self.fname])

    def end(self):
        pass

    def finalize(self, result):
        """Restore stdout.
        """

