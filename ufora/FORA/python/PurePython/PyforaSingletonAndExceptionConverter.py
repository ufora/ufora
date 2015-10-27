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

"""PyforaSingletonAndExceptionConverter

Converter for moving over instances of builtin exceptions (e.g. UserWarning, etc.),
and builtin objects like 'type', 'object', 'Exception', etc.

We need to implement these types directly in pure FORA because our primitives (like
PyInt) need them to throw appropriate exceptions.
"""
import pyfora.Exceptions as Exceptions
import ufora.native.FORA as ForaNative
import ufora.FORA.python.FORA as FORA
import pyfora.NamedSingletons as NamedSingletons
import logging
import traceback

class PyforaSingletonAndExceptionConverter:
    def __init__(self, pyforaBuiltinsModule):
        self.pyforaBuiltinsModule = pyforaBuiltinsModule
        self.pythonNameToInstance = {}
        self.instanceToPythonName = {}

        self.pyExceptionClass = pyforaBuiltinsModule.getObjectMember("PyException")
        self.invalidPyforaOperationClass = pyforaBuiltinsModule.getObjectMember("InvalidPyforaOperation")
        
        self.pyExceptionClassInstanceName = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (self.pyExceptionClass,
                    ForaNative.makeSymbol("CreateInstance"),
                    ForaNative.ImplValContainer(),
                    ForaNative.ImplValContainer()
                    )
                )
            ).getClassName()

        self.invalidPyforaOperationClassInstanceName = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (self.invalidPyforaOperationClass,
                    ForaNative.makeSymbol("CreateInstance"),
                    ForaNative.ImplValContainer()
                    )
                )
            ).getClassName()

        self.pythonNameToPyforaName = NamedSingletons.pythonNameToPyforaName

        for pyName, pyforaName in self.pythonNameToPyforaName.iteritems():
            instance = FORA.ForaValue.FORAValue(pyforaBuiltinsModule).__getattr__(pyforaName).implVal_

            self.pythonNameToInstance[pyName] = instance
            self.instanceToPythonName[instance] = pyName

    def convertSingletonByName(self, name):
        """Convert a singleton to an IVC by name, or None if it doesn't exist."""
        if name not in self.pythonNameToInstance:
            return None

        return self.pythonNameToInstance[name]

    def convertInstanceToSingletonName(self, instance):
        """Convert an IVC to a singleton name."""
        if instance not in self.instanceToPythonName:
            return None

        return self.instanceToPythonName[instance]

    def convertExceptionInstance(self, exceptionInstance):
        instanceClassName = exceptionInstance.getClassName()
        if instanceClassName == self.pyExceptionClassInstanceName:
            typeInstance = exceptionInstance.getObjectLexicalMember("@class")[0]
            typeInstanceName = self.convertInstanceToSingletonName(typeInstance)
            assert typeInstanceName is not None
            args = exceptionInstance.getObjectLexicalMember("@args")[0]

            return (typeInstanceName, args)
        return None

    def convertInvalidPyforaOperationInstance(self, instance):
        if instance.getClassName() == self.invalidPyforaOperationClassInstanceName:
            result = instance.getObjectLexicalMember("@message")[0]
            if not result.isString():
                raise Exceptions.ForaToPythonConversionError(
                    "InvalidPyforaOperation message should be a raw FORA string."
                    )
            return result.pyval

    def instantiateException(self, exceptionTypeName, exceptionArgsAsPyTuple):
        """Return an IVC representing an exception of type given by name 'exceptionTypeName'.

        Returns None if 'exceptionTypeName' isn't a singleton.
        """
        exceptionTypeInstance = self.convertSingletonByName(exceptionTypeName)
        if exceptionTypeInstance is None:
            return None

        args = (
            self.pyExceptionClass,
            ForaNative.makeSymbol("CreateInstance"),
            exceptionTypeInstance, 
            exceptionArgsAsPyTuple
            )

        return ForaNative.simulateApply(ForaNative.ImplValContainer(args))

