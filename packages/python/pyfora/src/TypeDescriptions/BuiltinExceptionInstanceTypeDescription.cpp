/***************************************************************************
   Copyright 2016 Ufora Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
****************************************************************************/
#include "../IRToPythonConverter.hpp"
#include "../NamedSingletons.hpp"
#include "BuiltinExceptionInstanceTypeDescription.hpp"


BuiltinExceptionInstanceTypeDescription::BuiltinExceptionInstanceTypeDescription(
        const std::string& typeName,
        int64_t argsId
        ) :
        mTypeName(typeName),
        mArgsId(argsId)
    {
    }


BuiltinExceptionInstanceTypeDescription::~BuiltinExceptionInstanceTypeDescription()
    {
    }


PyObject* BuiltinExceptionInstanceTypeDescription::transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObject* builtinExceptionType = 
        NamedSingletons::singletonNameToObject(mTypeName);
    if (builtinExceptionType == nullptr) {
        return nullptr;
        }
    
    PyObject* args = c.convert(mArgsId);
    if (args == nullptr) {
        Py_DECREF(builtinExceptionType);
        return nullptr;
        }

    PyObject* tr = PyObject_Call(
        builtinExceptionType,
        args,
        nullptr);

    Py_DECREF(args);
    Py_DECREF(builtinExceptionType);

    return tr;
    }
