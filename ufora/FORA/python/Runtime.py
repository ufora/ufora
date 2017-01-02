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

"""Runtime

Wrapper around the FORA Runtime, which must be initialized to actually execute FORA code.
"""
import os
import threading
import logging

import ufora.config.Setup as Setup
import ufora.util.ManagedThread as ManagedThread
import ufora.native

_curDir = os.path.split(os.path.abspath(__file__))[0]

import ufora.native.FORA as FORANative

#holds the global FORA runtime object
_mainRuntime = [None]
_mainRuntimeLock = threading.RLock()

def isInitialized():
    return _mainRuntime[0] is not None

def initialize(setupObjectToUse = None):
    if setupObjectToUse is None:
        configObjectToUse = Setup.config()
    else:
        configObjectToUse = setupObjectToUse.config

    with _mainRuntimeLock:
        if _mainRuntime[0] is not None:
            return
        #configure the main runtime compiler
        cfg = FORANative.RuntimeConfig()
        try:
            cfg.traceDefinitions = False
            cfg.traceArguments = False
            cfg.tracePaths = False
            cfg.useInlineMemoryManagement = True
            cfg.duplicateNativeEntrypoints = False
            cfg.validateVariablesDefinedBeforeUseInFlatCode = True
            cfg.inlineComplexity = 50
            cfg.dynamicInlinerSleepTimeMilliseconds = 50
            cfg.mediumPriorityCodeComplexityThreshold = 50
            cfg.useLLVMOptimization = True
            cfg.unrollHotLoopsWithComparisons = True
            cfg.enableDoubleVectorStashing = True
            cfg.kickIntoInterpreterOnInline = True
            cfg.disableSplitting = configObjectToUse.compilerDisableSplitting
            cfg.enableCodeExpansionRewriteRules = True

            cfg.applyRefcountOptimization = True

            cfg.extraDebugChecksDuringCompilation = False

            cfg.generateMachineCodeVectorAxioms = True

            cfg.sharedObjectLibraryPath = ufora.native.__file__
            cfg.compilerThreadCount = configObjectToUse.foraCompilerThreads

            cfg.compilerDefinitionDumpDir = configObjectToUse.compilerDefinitionDumpDir
            cfg.instructionDefinitionDumpDir = configObjectToUse.instructionDefinitionDumpDir

            cfg.dynamicInlineCallThreshold = 10000
            cfg.dynamicInlineCallThresholdSecondary = 5000

            cfg.maxDynamicInlineComplexity = 10000

            cfg.useDynamicInlining = True

            cfg.ptxLibraryPath = os.path.join(_curDir, "../CUDA/PTX/lib.ptx")
            cfg.compilerDiskCacheDir = configObjectToUse.compilerDiskCacheDir

            if cfg.compilerDefinitionDumpDir != "":
                logging.info("dumping CFGs to %s", cfg.compilerDefinitionDumpDir)
                try:
                    os.system("rm " + cfg.compilerDefinitionDumpDir + " -rf")
                except:
                    pass
                try:
                    os.makedirs(cfg.compilerDefinitionDumpDir)
                except:
                    pass


            axioms = open(os.path.join(_curDir,"../Axioms","axioms.fora"), "r").read()

            _mainRuntime[0] = FORANative.initializeRuntime(
                axioms,
                cfg,
                )

            if configObjectToUse.wantsPythonGilLoopChecker:
                ManagedThread.ManagedThread(
                    target = FORANative.checkPythonGilLoop,
                    args = (configObjectToUse.pythonGilLoopInterrupts,)
                    ).start()
        except:
            import traceback
            traceback.print_exc()
            raise

def getMainRuntime():
    """Returns the primary FORA runtime object. Throws if not initialized."""
    if _mainRuntime[0] is None:
        raise Setup.InitializationException("FORA Runtime is not initialized")
    return _mainRuntime[0]

