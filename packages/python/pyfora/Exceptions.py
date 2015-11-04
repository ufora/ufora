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

from concurrent.futures._base import Error, TimeoutError, CancelledError

import os
import linecache
import logging
import traceback

import pyfora
_pyforaRoot = os.path.split(pyfora.__file__)[0]

def renderTraceback(trace):
    res = []

    for tb in trace:
        if isinstance(tb["path"],tuple):
            path = tb["path"]
            if path[0] == "ModuleImporter":
                path = os.path.join(_pyforaRoot, *path[1:]) + ".fora"
            else:
                path = path[0]
        else:
            path = os.path.abspath(tb["path"])

        if 'range' in tb:
            lineNumber = tb['range']['start']['line']
        else:
            lineNumber = tb["line"]

        res.append('  File "%s", line %s' % (path, lineNumber))

        lines = linecache.getlines(os.path.abspath(path))
        if lines is not None and lineNumber >= 1 and lineNumber <= len(lines):
            res.append("    " + lines[lineNumber-1][:-1].lstrip())

    return "\n".join(res)

class PyforaError(Error):
    '''Base class for all pyfora exceptions.'''
    pass

class NotCallableError(PyforaError):
    '''An attempt was made to call a non-callable object.'''
    pass

class ComputationError(PyforaError):
    '''A remote computation resulted in an exception.'''
    def __init__(self, exceptionValue, trace):
        self.exceptionValue = exceptionValue
        self.trace = trace

    def __str__(self):
        if self.trace is None:
            return "%s" % self.exceptionValue

        try:
            return "%s\n%s" % (str(self.exceptionValue), renderTraceback(self.trace))
        except:
            logging.error("%s", traceback.format_exc())
            raise

    def __repr__(self):
        return "ComputationError(exceptionValue=%s,trace=%s)" % (self.exceptionValue, self.trace)

class PythonToForaConversionError(PyforaError):
    '''Unable to convert the specified Python object.'''
    def __init__(self, message, trace=None):
        """Initialize a conversion error.

        message - a string containing the error message
        trace - None, or a list of the form [
            {'path':str, 'line': int},
            ...
            ]
        """
        self.message = message
        self.trace = trace

    def __str__(self):
        if self.trace is None:
            return self.message
        else:
            return "%s\n%s" % (self.message, renderTraceback(self.trace))

    def __repr__(self):
        return "PythonToForaConversionError(message=%s,trace=%s)" % (repr(self.message), repr(self.trace))

class ForaToPythonConversionError(PyforaError):
    '''Unable to convert the specified object to Python.'''
    pass

class InternalError(PyforaError):
    '''Error resulting because the code has bugs (e.g., improper use of an API).'''
    pass

class PyforaNotImplementedError(PyforaError):
    '''Feature not yet implemented in Pyfora.'''
    pass

class InvalidPyforaOperation(PyforaError):
    """Pyfora cannot faithfully execute this code."""

class CantGetSourceTextError(PyforaError):
    pass

class ResultExceededBytecountThreshold(PyforaError):
    pass


