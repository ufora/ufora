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
import pyfora.PyforaInspect as PyforaInspect
import logging
import traceback

import pyfora
_pyforaRoot = os.path.split(pyfora.__file__)[0]

def checkTraceElement(elmt):
    assert isinstance(elmt, dict)
    assert 'path' in elmt
    assert isinstance(elmt['path'], tuple) or isinstance(elmt['path'], str)
    assert 'range' in elmt or 'line' in elmt

def makeTraceElement(path, lineNumber):
    return {'path': path, 'line': lineNumber}

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

        from pyfora.pyAst.PyAstUtil import findEnclosingFunctionName, getAstFromFilePath
        inFunction = findEnclosingFunctionName(
            getAstFromFilePath(path),
            lineNumber
            ) if path.endswith(".py") else None
        if inFunction is not None:
            res.append('  File "%s", line %s, in %s' % (path, lineNumber, inFunction))
        else:
            res.append('  File "%s", line %s' % (path, lineNumber))

        lines = PyforaInspect.getlines(path)
        if lines is not None and lineNumber >= 1 and lineNumber <= len(lines):
            res.append("    " + lines[lineNumber-1][:-1].lstrip())

    return "\n".join(res)

class PyforaError(Error):
    '''Base class for all pyfora exceptions.'''
    pass

class NotCallableError(PyforaError):
    '''Raised when an attempt is made to call a non-callable object.'''
    pass

class ComputationError(PyforaError):
    '''Raised when a remote computation results in an exception.

    Args:
        remoteException (Exception): The exception raised by the remote computation.
        trace (Optional[List]): A representation of the stack trace in which the exception was raised.
            It takes the form: ``[{'path':str, 'line': int}, ...  ]``
    '''
    def __init__(self, remoteException, trace):
        self.remoteException = remoteException
        self.trace = trace

    def __str__(self):
        if self.trace is None:
            return "%s" % self.remoteException

        try:
            return "%s\n%s" % (str(self.remoteException), renderTraceback(self.trace))
        except:
            logging.error("%s", traceback.format_exc())
            raise

    def __repr__(self):
        return "ComputationError(remoteException=%s,trace=%s)" % (self.remoteException, self.trace)

    @property
    def message(self):
        return repr(self)

class PythonToForaConversionError(PyforaError):
    '''Raised when an attempt is made to use a Python object that cannot be remoted by ``pyfora``.

    This may happen when, for example:

       - A function attempts to mutate state or produce side-effect (i.e. it is not "purely functional").

       - A call is made to a Python builtin that is not supported by ``pyfora`` (e.g. :func:`open`)

    Args:
        message (str): Error message.
        trace (Optional[List]): A representation of the stack trace in which the exception was raised.
            It takes the form: ``[{'path':str, 'line': int}, ...  ]``
    '''
    def __init__(self, message, trace=None):
        self.message = message
        self.trace = trace

    def __str__(self):
        if self.trace is None:
            return str(self.message)
        else:
            return "%s\n%s" % (self.message, renderTraceback(self.trace))

    def __repr__(self):
        return "PythonToForaConversionError(message=%s,trace=%s)" % (repr(self.message), repr(self.trace))

class ForaToPythonConversionError(PyforaError):
    '''Raised when attempting to download a remote object that cannot be converted to Python.'''
    pass

class InternalError(PyforaError):
    '''Error resulting because the code has bugs (e.g., improper use of an API).'''
    pass

class PyforaNotImplementedError(PyforaError):
    '''Feature not yet implemented in ``pyfora``.'''
    pass

class CantGetSourceTextError(PyforaError):
    pass

class ResultExceededBytecountThreshold(PyforaError):
    '''Raised when attempting to download a remote object whose size exceeds the specified maximum.'''
    pass

class ConnectionError(PyforaError):
    '''Raised when a connection to the pyfora backend cannot be established.'''
    pass

class BadWithBlockError(PyforaError):
    '''Raised when a pyfora with block has an illegal construct,
    such as a yield or return statement'''
    pass

class UnconvertibleValueError(Exception):
    # it's important for the way WithBlock tracebacks are rendered that
    # this class NOT be a PyforaError
    pass

class InvalidPyforaOperation(Exception):
    # it's important for the way WithBlock tracebacks are rendered that
    # this class NOT be a PyforaError
    '''Raised when a running computation performs an operation that cannot be faithfully executed with ``pyfora``.'''

