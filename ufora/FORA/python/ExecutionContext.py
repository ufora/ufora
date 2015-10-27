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
import threading
import time
import logging
import sys
import ufora.FORA.VectorDataManager.VectorDataManager as VectorDataManager
import ufora.config.Setup as Setup

import ufora.native

_curDir = os.path.split(os.path.abspath(__file__))[0]

import ufora.native.FORA as FORANative

def configureContextConfiguration(
                        configuration,
                        allowInterpreterTracing = True,
                        blockUntilTracesAreCompiled = False
                        ):
    configuration.allowInterpreterTracing = allowInterpreterTracing
    configuration.blockUntilTracesAreCompiled = blockUntilTracesAreCompiled

def createContextConfiguration(*args, **kwds):
    configuration = FORANative.ExecutionContextConfiguration.defaultConfiguration()
    
    configureContextConfiguration(configuration, *args, **kwds)

    return configuration
    

def ExecutionContext(	stackIncrement = 32 * 1024,
                        dataManager = None,
                        allowInterpreterTracing = True,
                        blockUntilTracesAreCompiled = False
                        ):
    """Create a new execution context and return it"""
    
    assert dataManager is not None

    tr = FORANative.ExecutionContext(dataManager, stackIncrement)
    
    configureContextConfiguration(
            tr.configuration, 
            allowInterpreterTracing,
            blockUntilTracesAreCompiled
            )

    return tr


def simpleEval(callbackScheduler, *args):
    """convert 'args' to FORA ImplValContainers, evaluates, and returns a python value.
    
    Assumes you don't use cache or vector loads.  If you return an exception, this function
    asserts false. Otherwise, it returns the ImplValContainer result.
    """
    e = ExecutionContext(
        dataManager = VectorDataManager.constructVDM(callbackScheduler)
        )
    e.evaluate(*[FORANative.ImplValContainer(x) for x in args])
    tr = e.getFinishedResult()
    if tr.isFailure():
        assert False
    if tr.isException():
        assert False
    try:
        return tr.asResult.result.pyval
    except:
        return tr.asResult.result
        


