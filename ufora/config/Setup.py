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

'''The setup module is required at every mainline entrypoint to the system.
Unless this module is explicitly initalized then nothing should work and an exception should be
thrown.
'''

import ufora.util.ThreadLocalStack as ThreadLocalStack
import ufora.config.Config as Config
import logging
import argparse
import os
import re

DEFAULT_CONFIG_ENV_VARNAME = 'BSA_CONFIG_FILE'

class InitializationException(Exception):
    pass

def addDefaultArguments(parser):
    addCredentialsParser(parser)
    addLoggingParser(parser)
    addSystemResourcesParser(parser)

def addCredentialsParser(parser):
    parser.add_argument(
            '-u',
            '--user',
            dest='user',
            required=False,
            help='Username to login to the cluster'
            )
    parser.add_argument(
            '-p',
            '--password',
            dest='password',
            required=False,
            help='Password to the cluster'
            )
    parser.add_argument(
            '-c',
            '--cluster',
            dest='cluster',
            required=False,
            help="Host name and, optionally, HTTPS port of the target cluster."
            )

def addLoggingParser(parser):
    parser.add_argument(
            "--logging",
            required=False,
            default='warn',
            choices=['debug', 'info', 'warn', 'error'],
            help = "Sets the logging level"
            )
    parser.add_argument(
            "--background-logging",
            dest='background_logging',
            required=False,
            default=None,
            choices=['debug', 'info', 'warn', 'error'],
            help = "Sets the logging level of background processes"
            )
    parser.add_argument(
            "--stack-logfile-path",
            dest='stackLogfile',
            required=False,
            help = "log stacktraces in the background"
            )

def addSystemResourcesParser(parser):
    '''
    Add a arguments to specify writable directories / ports, etc
    '''
    parser.add_argument(
            "--dataroot",
            required=False,
            help = "specify an alternate location for data that the application produces"
            )

    parser.add_argument(
            "--datarootsubdir",
            required=False,
            help = "specify an additional subdirectory to add to the dataroot"
            )

    parser.add_argument(
            "--baseport",
            required=False,
            help = "specify and alternate base port",
            type=int
            )

    parser.add_argument(
            "--interpreterTraceDumpFile",
            dest='interpreterTraceDumpFile',
            required=False,
            help = "dump interpreter traces to this file if provided.",
            type=str
            )

def defaultParser(minimalParser=False, **kwds):
    """Create a parser that has basic overrides for Config.py

    kwds - passed directly to the argparse.ArgumentParser constructor.
    """
    parser = argparse.ArgumentParser(**kwds)
    addCredentialsParser(parser)
    if not minimalParser:
        addLoggingParser(parser)
        addSystemResourcesParser(parser)

    return parser


class Setup(object):
    def __init__(self, configObject):
        self.config = configObject

    def processArgs(self, parsedArguments):
        """Update the Setup's config to reflect parsedArguments.

        parsedArguments - the result of an argparse parse action.
        """
        parsed = parsedArguments

        if 'interpreterTraceDumpFile' in parsed and parsed.interpreterTraceDumpFile:
            self.config.interpreterTraceDumpFile = parsed.interpreterTraceDumpFile

        if 'stackLogfile' in parsed and parsed.stackLogfile:
            self.config.backgroundStackTraceLoopFilename = parsed.stackLogfile

        if 'logging' in parsed and parsed.logging:
            self.config.setLoggingLevel(parsed.logging, parsed.background_logging)

        if 'target' in parsed and parsed.target:
            self.config.target = parsed.target

        if 'dataroot' in parsed and parsed.dataroot:
            path = os.path.expanduser(parsed.dataroot)
            self.config.setRootDataDir(path)

        if 'datarootsubdir' in parsed and parsed.datarootsubdir:
            path = os.path.join(self.config.rootDataDir, parsed.datarootsubdir)
            self.config.setRootDataDir(path)

        if 'baseport' in parsed and parsed.baseport:
            self.config.setAllPorts(parsed.baseport)

        self.parsedArguments = parsedArguments


class PushSetup(ThreadLocalStack.ThreadLocalStackPushable):
    '''
    Push a config with no user information. This is useful for
    entrypoints where a username is eventually supplied by the
    user
    '''
    def __init__(self, setup):
        super(PushSetup, self).__init__()
        self._setup = setup

def config():
    tr = PushSetup.getCurrent()
    if tr is None:
        raise InitializationException('setup object not found')
    return tr._setup.config

def currentSetup():
    tr = PushSetup.getCurrent()
    if tr is not None:
        return tr._setup
    return tr


def readConfigDictFromFilename(fileName):
    _vardefRE = re.compile("\s*(\w*)\s*=\s*([^\n]*)")
    configData = dict()
    fileText = readFileTextIfExists(fileName)

    fileLines = fileText.split("\n")
    for l in fileLines:
        m = _vardefRE.match(l)
        if m is not None:
            configData[m.groups()[0]] = m.groups()[1].strip()
    return configData

def readFileTextIfExists(fileName):
    fileText = ""
    try:
        with open(fileName, "r") as f:
            fileText = f.read()
    except IOError:
        pass
    return fileText


def _defaultConfigFilenameFromEnvironment():
    """return the system-default config file.

    If BSA_CONFIG_FILE is set, we use that. Otherwise, we use a project-local config.cfg
    """
    if DEFAULT_CONFIG_ENV_VARNAME in os.environ:
        return os.environ[DEFAULT_CONFIG_ENV_VARNAME]
    else:
        logging.info("using default config file")
        return os.path.join(os.path.split(__file__)[0], 'config.cfg')

def _createConfigFromFile(filename=None):
    '''creates a config object from a given filename if it exists, otherwise it tries in './config.cfg'''
    return createConfig(filename)


def createConfig(filename=None, overrides = None):
    """create a config file from 'filename' and 'overrides'

    filename should be a path to a .cfg file. if none, we use ./config.cfg
    overrides should be a dictionary of additional flags to override.
    """
    if filename is None:
        filename = _defaultConfigFilenameFromEnvironment()

    configDict = readConfigDictFromFilename(filename)

    if overrides is not None:
        configDict.update(overrides)

    return Config.Config(configDict)


def defaultSetup():
    config = _createConfigFromFile()
    return Setup(config)



