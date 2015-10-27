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
        return "ComputationError(exceptionValue=" + str(self.exceptionValue) + ",trace=" + str(self.trace) + ")"

    def __repr__(self):
        return "ComputationError(exceptionValue=" + repr(self.exceptionValue) + ",trace=" + str(self.trace) + ")"

class PythonToForaConversionError(PyforaError):
    '''Unable to convert the specified Python object.'''
    pass

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


