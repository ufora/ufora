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

import sys
import os
import ufora.config.Setup as Setup
import argparse
import nose
import nose.plugins.xunit

import ufora.test.UnitTestCommon as UnitTestCommon
import ufora.config.LoginConfiguration as LoginConfiguration

import ufora.native.CallbackScheduler as CallbackScheduler

from ufora.test.OutputCaptureNosePlugin import OutputCaptureNosePlugin

def addNoseVerbosityArgument(parser):
    parser.add_argument(
        '-v',
        dest='testHarnessVerbose',
        action='store_true',
        default=False,
        required=False,
        help="run test harness verbosely"
        )

def UnitTestMainline(modulesToInitialize=None,
                     exit=True,
                     loginConfiguration=LoginConfiguration.LoginConfiguration.defaultForTesting(),
                     disableLogCapture=False):
    """Helper function to call the unittest mainline

    Constructs a default Setup from the config. Calls
        x.initialize(setup)
    for all x in modulesToInitialize.
    """
    modulesToInitialize = modulesToInitialize or []
    import ufora.native

    argv = list(sys.argv)
    setup = Setup.defaultSetup()

    parser = Setup.defaultParser()

    unitTestOptions = parser.add_argument_group(
        title='UnitTestMainline options',
        description='options for the general UnitTest framework'
        )
    addNoseVerbosityArgument(unitTestOptions)

    unitTestOptions.add_argument(
        'testHarnessArguments',
        nargs=argparse.REMAINDER
        )

    parser.add_argument('-timeout',
                        type=float,
                        nargs=1,
                        help='fail test if not completed after TIMEOUT seconds',
                        default=None)

    parsedArguments = parser.parse_args(argv[1:])

    if parsedArguments.timeout is not None:
        UnitTestCommon.startTimeoutThread(parsedArguments.timeout[0])

    setup.processArgs(parsedArguments)

    testHarnessArguments = ["dummy"] + parsedArguments.testHarnessArguments

    testHarnessArguments.append('--verbosity=0')

    if parsedArguments.testHarnessVerbose or disableLogCapture:
        testHarnessArguments.append('--nocaptureall')
    setup.config.configureLoggingForUserProgram()

    plugins = nose.plugins.manager.PluginManager([OutputCaptureNosePlugin()])


    config = nose.config.Config(plugins=plugins)
    config.configure(testHarnessArguments)

    with Setup.PushSetup(setup):
        result = None
        for toInitialize in modulesToInitialize:
            toInitialize.initialize(setup)

        result = nose.core.TestProgram(
            exit=False,
            defaultTest="__main__",
            config=config,
            argv=testHarnessArguments
            ).success

        sys.stdout.flush()
        sys.stderr.flush()
        ufora.native.Tests.gcov_flush()

        if not exit:
            return 0 if result else 1
        else:
            os._exit(0 if result else 1)


def UserFacingMainline(main, argv, modulesToInitialize=None, parser=None):
    """Helper function that initializes some modules and then calls main.

    Used to centralize error handling for common initialization routines and to set up the
    initial component hosts.
    """
    if parser is None:
        parser = Setup.defaultParser()

    setup = Setup.defaultSetup()

    parsedArguments = parser.parse_args(argv[1:])
    setup.processArgs(parsedArguments)

    setup.config.configureLoggingForUserProgram()

    with Setup.PushSetup(setup):
        initializeModules(modulesToInitialize)

        result = main(parsedArguments)

        if result is None:
            result = 0

        sys.stdout.flush()
        sys.stderr.flush()

        os._exit(result)


_callbackSchedulerFactory = None
def getCallbackSchedulerFactory():
    global _callbackSchedulerFactory
    if _callbackSchedulerFactory is None:
        _callbackSchedulerFactory = CallbackScheduler.createSimpleCallbackSchedulerFactory()
    return _callbackSchedulerFactory

def initializeModules(modulesToInitialize):
    if modulesToInitialize is not None:
        for module in modulesToInitialize:
            module.initialize()


