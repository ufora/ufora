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

#read in config.cfg
#if its not there, seed an empty one and try to fill it out as best you can
#export values from config.cfg as module members so that people can query the install
import logging
import json
import sys
import psutil
import os
import os.path
import ufora.config.LogFormat as LogFormat
import ufora.util.StackTraceLoop as StackTraceLoop


def parseBool(arg):
    if isinstance(arg, bool):
        return arg

    if isinstance(arg, str):
        if arg.upper() in ("TRUE", "T"):
            return True
        if arg.upper() in ("FALSE", "F"):
            return False
        if arg == "":
            return False

    try:
        anInt = int(arg)
        return bool(anInt)
    except ValueError:
        pass

    raise ValueError("Can't convert '%s' to a bool. Use an integer or True/False" % repr(arg))

def expandConfigPath(path):
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return path

logLevels = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARN,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
    }

def stringToLogLevel(levelStr):
    levelStr = levelStr.upper()

    if levelStr in logLevels:
        return logLevels[levelStr]

    assert False, "%s is not a valid log level" % levelStr

def maxLocalThreads():
    import multiprocessing
    localThreads = multiprocessing.cpu_count()
    if localThreads > 8:
        # reserve 2 cores for the compiler
        localThreads -= 2
    return localThreads

def linearInRange(minX, minY, maxX, maxY, x):
    '''
    Returns minY or maxY if x is outside [minX, maxX] range. Otherwise,
    returns the value for x of the linear function between min and max.
    '''
    if x <= minX:
        return minY
    elif x >= maxX:
        return maxY
    return (x - minX) * (maxY - minY)/(maxX - minX) + minY


class Config(object):
    def getConfigValue(self, s, default=None, checkEnviron=False):
        """return configuration string for 's'. returns 'default' if not there"""
        if s in self._configData:
            return self._configData[s]
        elif checkEnviron and s in os.environ:
            return os.environ[s]
        else:
            return default

    def __init__(self, configData):
        self.logHandler = None

        self._configData = configData

        self._configDir = os.path.split(__file__)[0]

        rootDataDir = expandConfigPath(
            self.getConfigValue("ROOT_DATA_DIR",
                                default=os.path.join(os.path.expanduser('~'), '.ufora'),
                                checkEnviron=True)
            )
        self.setRootDataDir(rootDataDir)

        self.setAllPorts(int(self.getConfigValue("BASE_PORT", 30000)))

        # FORA CONFIG
        self.maxLocalThreads = int(self.getConfigValue("MAX_LOCAL_THREADS", -1))
        if self.maxLocalThreads == -1:
            self.maxLocalThreads = maxLocalThreads()

        self.wantsPythonGilLoopChecker = parseBool(
            self.getConfigValue("START_PYTHON_GIL_LOOP_THREAD", False)
            )
        self.pythonGilLoopInterrupts = parseBool(
            self.getConfigValue("PYTHON_GIL_LOOP_THREAD_INTERRUPTS", False)
            )

        self.maxMemoryMB = long(self.getConfigValue("FORA_MAX_MEM_MB",
                                                    (psutil.virtual_memory().total * 0.75) / (1024 ** 2),
                                                    checkEnviron=True))
        self.cumulusTrackTcmalloc = parseBool(self.getConfigValue("CUMULUS_TRACK_TCMALLOC",
                                                                  default=True,
                                                                  checkEnviron=True))
        self.setCumulusMemoryBounds(self.cumulusTrackTcmalloc)

        # Cumulus options
        self.cumulusMaxRamCacheMB = self.maxMemoryMB - \
            long(linearInRange(8000, self.cumulusOverflowBufferMbLower,
                               60000, self.cumulusOverflowBufferMbUpper,
                               self.maxMemoryMB))
        self.cumulusVectorRamCacheMB = self.cumulusMaxRamCacheMB - \
            long(linearInRange(7000, self.vdmOverflowBufferMbLower,
                               25000, self.vdmOverflowBufferMbUpper,
                               self.cumulusMaxRamCacheMB))

        self.computedValueGatewayRAMCacheMB = long(
            self.getConfigValue("COMPUTED_VALUE_GATEWAY_RAM_MB", 400)
            )

        self.cumulusDiskCacheStorageMB = int(self.getConfigValue("CUMULUS_DISK_STORAGE_MB", 50000))
        self.cumulusDiskCacheStorageFileCount = int(
            self.getConfigValue("CUMULUS_DISK_STORAGE_FILE_COUNT", 10000)
            )
        self.cumulusServiceThreadCount = long(self.getConfigValue("FORA_WORKER_THREADS",
                                                                  self.maxLocalThreads))

        self.cumulusCheckpointIntervalSeconds = long(
            self.getConfigValue("CUMULUS_CHECKPOINT_COMMIT_INTERVAL_SEC", 0)
            )

        self.cumulusDiskCacheStorageSubdirectory = None

        self.maxPageSizeInBytes = long(
            self.getConfigValue("CUMULUS_VECTOR_MAX_CHUNK_SIZE_BYES", 20 * 1024 * 1024)
            )

        self.externalDatasetLoaderThreadcount = long(
            self.getConfigValue("EXTERNAL_DATASET_LOADER_THREADS", 5)
            )
        self.externalDatasetLoaderServiceThreads = long(
            self.getConfigValue("EXTERNAL_DATASET_LOADER_SERVICE_THREADS", 1)
            )

        self.userDataS3Bucket = self.getConfigValue("USER_DATA_BUCKET", 'ufora.user.data')

        self.foraCompilerThreads = long(
            self.getConfigValue("FORA_COMPILER_THREADS",
                                2 if self.maxLocalThreads < 4 else 4)
            )

        if sys.platform == "linux2":
            import resource
            resource.setrlimit(resource.RLIMIT_AS, (self.maxMemoryMB * 1024 * 1024, -1))


        self.foregroundLoggingLevel = logging.WARN
        self.backgroundLoggingLevel = logging.INFO

        self.backgroundStackTraceLoopFilename = None

        # LOGGING_OVERRIDES may be empty, or may contain a list of tuples.
        # Each tuple should look like (scopeRegex, fileRegex, logLevel)
        loggingLevelOverridesString = self.getConfigValue("LOGGING_OVERRIDES", None)
        if loggingLevelOverridesString:
            overrides = json.loads(loggingLevelOverridesString)
            self.scopedLoggingLevelOverrides = []

            for scopeRegex, fileRegex, level in overrides:
                newLevel = stringToLogLevel(level)

                self.scopedLoggingLevelOverrides.append((str(scopeRegex), str(fileRegex), newLevel))
        else:
            self.scopedLoggingLevelOverrides = None

    def setCumulusMemoryBounds(self, isTrackingTcMalloc):
        defaultRamCacheBounds = (1000, 4000) if isTrackingTcMalloc else (1000, 10000)
        defaultVdmBounds = (1000, 4000) if isTrackingTcMalloc else (500, 4000)

        self.cumulusOverflowBufferMbLower = long(
            self.getConfigValue("CUMULUS_OVERFLOW_BUFFER_MB_LOWER", defaultRamCacheBounds[0])
            )
        self.cumulusOverflowBufferMbUpper = long(
            self.getConfigValue("CUMULUS_OVERFLOW_BUFFER_MB_UPPER", defaultRamCacheBounds[1])
            )

        self.vdmOverflowBufferMbLower = long(self.getConfigValue("VDM_OVERFLOW_BUFFER_MB_LOWER",
                                                                 defaultVdmBounds[0]))
        self.vdmOverflowBufferMbUpper = long(self.getConfigValue("VDM_OVERFLOW_BUFFER_MB_UPPER",
                                                                 defaultVdmBounds[1]))


    def setAllPorts(self, basePort, numPorts=100):
        self.basePort = basePort
        self.relayPort = \
            int(self.getConfigValue('UFORA_WEB_HTTP_PORT', 0)) or basePort
        self.numPorts = numPorts
        self.sharedStatePort = basePort + 2
        self.appServerPort = basePort + 3
        self.fakeEc2Port = basePort + 4
        self.relayHttpsPort = \
            int(self.getConfigValue('UFORA_WEB_HTTPS_PORT', 0)) or basePort + 5
        self.restApiPort = basePort + 6
        self.relayTcpPort = basePort + 7
        self.subscribableWebObjectsPort = basePort + 8

        self.cumulusControlPort = \
            int(self.getConfigValue("UFORA_WORKER_CONTROL_PORT", 0)) or basePort + 9
        self.cumulusDataPort = \
            int(self.getConfigValue("UFORA_WORKER_DATA_PORT", 0)) or self.cumulusControlPort + 1
        self.testPort = basePort + 50


    def setRootDataDir(self, rootDataDir, ensureExists=True):
        '''
        Sets the root data directory and all others that derive from it
        '''
        rootDataDir = os.path.abspath(rootDataDir)

        self.rootDataDir = rootDataDir

        if ensureExists:
            if not os.path.exists(rootDataDir):
                os.makedirs(rootDataDir)

        if parseBool(self.getConfigValue("FORA_COMPILER_DUMP_NATIVE_CODE", False)):
            self.compilerDefinitionDumpDir = os.path.join(self.rootDataDir, "dumps")
        else:
            self.compilerDefinitionDumpDir = ""

        if parseBool(self.getConfigValue("FORA_COMPILER_DUMP_INSTRUCTIONS", False)):
            self.instructionDefinitionDumpDir = os.path.join(self.rootDataDir, "dumps")
        else:
            self.instructionDefinitionDumpDir = ""

        if parseBool(self.getConfigValue("FORA_COMPILER_DUMP_TRACES", False)):
            self.interpreterTraceDumpFile = os.path.join(self.rootDataDir, "dumps", "traces")
        else:
            self.interpreterTraceDumpFile = ""


        self.objectStore = self.getConfigValue('OBJECT_STORE', 's3')
        self.objectStoreMaxAttempts = int(self.getConfigValue('OBJECT_STORE_MAX_ATTEMPTS',
                                                              100))
        self.objectStoreFailureInterval = float(self.getConfigValue('OBJECT_STORE_FAILURE_INTERVAL',
                                                                    20))
        self.hdfsNameNodeHost = self.getConfigValue('OBJECT_STORE_HDFS_NAME_NODE_HOST',
                                                    'hdfs')
        self.hdfsNameNodePort = self.getConfigValue('OBJECT_STORE_HDFS_NAME_NODE_PORT',
                                                    '50070')
        self.hdfsObjectStoreRootDir = self.getConfigValue('OBJECT_STORE_HDFS_ROOT_DIR',
                                                          '/ufora/object-store')


        self.fakeAwsBaseDir = self.getConfigValue("FAKE_AWS_DIR",
                                                  os.path.join(self.rootDataDir, 'fakeAws'))

        self.sharedStateLogPruneFrequency = int(self.getConfigValue(
            "SHARED_STATE_LOG_PRUNE_FREQUENCY",
            60 * 60))

        self.sharedStateCache = str(self.getConfigValue("SHARED_STATE_CACHE",
                                                        os.path.join(self.rootDataDir, "ss_cache")))

        self.cumulusDiskCacheStorageDir = self.getConfigValue(
            "CUMULUS_DISK_STORAGE_DIR",
            self.rootDataDir + os.sep + "cumulus_disk_storage"
            )

        self.cumulusEventsPath = os.path.join(self.rootDataDir, "cumulus_events")


    def setLoggingLevel(self, foregroundLevel, backgroundLevel=None):
        if backgroundLevel is not None:
            self.backgroundLoggingLevel = stringToLogLevel(backgroundLevel)

        if foregroundLevel is not None:
            self.foregroundLoggingLevel = stringToLogLevel(foregroundLevel)

    def copyLoggingSettings(self, other):
        self.foregroundLoggingLevel = other.foregroundLoggingLevel
        self.backgroundLoggingLevel = other.backgroundLoggingLevel
        self.scopedLoggingLevelOverrides = other.scopedLoggingLevelOverrides

    def setNativeLoggingLevel(self, level):
        validLevels = (logging.DEBUG, logging.INFO, logging.WARN, logging.ERROR, logging.CRITICAL)
        assert level in validLevels
        import ufora.native.Logging as NativeLogging
        NativeLogging.setLogLevel(level)

    def configureLogging(self, level):
        logging.getLogger().setLevel(level)
        self.setNativeLoggingLevel(level)

        if self.logHandler is not None:
            logging.getLogger().removeHandler(self.logHandler)
        if logging.getLogger().handlers:
            logging.getLogger().handlers = []

        handler = LogFormat.createFormatedLogHandler(level)
        logging.getLogger().addHandler(handler)
        self.logHandler = handler

        if self.scopedLoggingLevelOverrides:
            import ufora.native.Logging as NativeLogging

            for scopeRegex, fileRegex, level in self.scopedLoggingLevelOverrides:
                NativeLogging.setScopedLoggingLevel(scopeRegex, fileRegex, level)

    def startBackgroundStackTraceLoop(self):
        if self.backgroundStackTraceLoopFilename is not None:
            StackTraceLoop.startLoop(self.backgroundStackTraceLoopFilename, timeout=2.0)

    def configureLoggingForUserProgram(self):
        self.startBackgroundStackTraceLoop()
        self.configureLogging(self.foregroundLoggingLevel)

    def configureLoggingForBackgroundProgram(self):
        self.configureLogging(self.backgroundLoggingLevel)


