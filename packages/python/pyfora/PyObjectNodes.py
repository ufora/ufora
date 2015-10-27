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

class PyObjectNode(object):
    pass


class Primitive(PyObjectNode):
    def __init__(self, pyObject):
        self.pyObject = pyObject


class File(PyObjectNode):
    def __init__(self, path, pyObject):
        self.path = path
        self.pyObject = pyObject


class FunctionDefinition(PyObjectNode):
    def __init__(
            self,
            pyObject,
            sourceFile,
            lineNumber,
            freeVariableMemberAccessChainResolutions
            ):
        self.pyObject = pyObject
        self.sourceFile = sourceFile
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainResolutions = \
            freeVariableMemberAccessChainResolutions


class ClassDefinition(PyObjectNode):
    def __init__(
            self,
            pyObject,
            sourceFile,
            lineNumber,
            freeVariableMemberAccessChainResolutions
            ):
        self.pyObject = pyObject
        self.sourceFile = sourceFile
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainResolutions = \
            freeVariableMemberAccessChainResolutions


class ClassInstanceDescription(PyObjectNode):
    def __init__(
            self,
            pyObject,
            klass,
            classMemberNameToMemberValue
            ):
        self.pyObject = pyObject
        self.klass = klass
        self.classMemberNameToMemberValue = classMemberNameToMemberValue


class List(PyObjectNode):
    def __init__(self, pyObject):
        self.pyObject = pyObject


class Tuple(PyObjectNode):
    def __init__(self, pyObject):
        self.pyObject = pyObject


class Dict(PyObjectNode):
    def __init__(self, pyObject):
        self.pyObject = pyObject


class WithBlock(PyObjectNode):
    def __init__(
            self,
            pyObject,
            fileObject,
            sourceLine,
            freeVariableMemberAccessChainResolutions
            ):
        self.pyObject = pyObject
        self.sourceFile = fileObject
        self.lineNumber = sourceLine
        self.freeVariableMemberAccessChainResolutions = \
            freeVariableMemberAccessChainResolutions

class RemotePythonObject(PyObjectNode):
    def __init__(self, remotePythonObject):
        self.pyObject = remotePythonObject
        self.computedValueArg = remotePythonObject._pyforaComputedValueArg()

class NamedSingleton(PyObjectNode):
    def __init__(self, pyObject, singletonName):
        self.pyObject = pyObject
        self.singletonName = singletonName

class BuiltinExceptionInstance(PyObjectNode):
    def __init__(self, pyObject, builtinExceptionTypeName, args):
        self.pyObject = pyObject
        self.builtinExceptionTypeName = builtinExceptionTypeName
        self.args = args

