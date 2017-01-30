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
import pyfora.Exceptions as Exceptions

import logging
import traceback


class UnresolvedFreeVariableException(Exception):
    def __init__(self, freeVariable, contextName):
        super(UnresolvedFreeVariableException, self).__init__()
        self.freeVarChainWithPos = freeVariable
        self.contextNameOrNone = contextName


class UnresolvedFreeVariableExceptionWithTrace(Exception):
    def __init__(self, message, trace=None):
        super(UnresolvedFreeVariableExceptionWithTrace, self).__init__()
        self.message = message
        if trace is None:
            self.trace = []
        else:
            self.trace = trace
    def addToTrace(self, elmt):
        Exceptions.checkTraceElement(elmt)
        self.trace.insert(0, elmt)


def getUnresolvedFreeVariableExceptionWithTrace(e, sourceFileName):
    chainWithPos = e.freeVarChainWithPos
    varLine = chainWithPos.pos.lineno
    varName = chainWithPos.var[0]

    return UnresolvedFreeVariableExceptionWithTrace(
        '''unable to resolve free variable '%s' for pyfora conversion''' % varName,
        [Exceptions.makeTraceElement(sourceFileName, varLine)]
        )


def convertUnresolvedFreeVariableExceptionAndRaise(e, sourceFileName):
    logging.error(
        "Converter raised an UnresolvedFreeVariableException exception: %s",
        traceback.format_exc())
    raise getUnresolvedFreeVariableExceptionWithTrace(e, sourceFileName)
