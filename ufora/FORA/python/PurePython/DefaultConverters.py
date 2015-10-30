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

import ufora.FORA.python.ModuleImporter as ModuleImporter

import pyfora

import ufora.native.FORA as ForaNative

builtinPythonImplVal = ModuleImporter.importModuleFromPath(
    os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora", "purePython"),
    searchForFreeVariables=True
    )

primitiveTypeMapping = {
    bool: builtinPythonImplVal.getObjectMember("PyBool"),
    str: builtinPythonImplVal.getObjectMember("PyString"),
    int: builtinPythonImplVal.getObjectMember("PyInt"),
    float: builtinPythonImplVal.getObjectMember("PyFloat"),
    type(None): builtinPythonImplVal.getObjectMember("PyNone"),
    }

defaultWrappingNativeListConverter = ForaNative.makeWrappingPythonListConverter(
    builtinPythonImplVal.getObjectMember("PyList")
    )

defaultWrappingNativeTupleConverter = ForaNative.makePythonTupleConverter(
    builtinPythonImplVal.getObjectMember("PyTuple")
    )

defaultWrappingNativeDictConverter = ForaNative.makeWrappingPythonDictConverter(
    builtinPythonImplVal.getObjectMember("PyDict")
    )

