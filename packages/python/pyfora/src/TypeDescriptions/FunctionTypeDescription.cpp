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
#include "../PythonObjectRehydrator.hpp"
#include "FunctionTypeDescription.hpp"

#include <stdexcept>


FunctionTypeDescription::FunctionTypeDescription(
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions
    ) :
        mSourceFileId(sourceFileId),
        mLinenumber(linenumber),
        mFreeVariableResolutions(freeVariableResolutions)
    {
    Py_XINCREF(mFreeVariableResolutions);
    }


FunctionTypeDescription::~FunctionTypeDescription()
    {
    Py_XDECREF(mFreeVariableResolutions);
    }


PyObject* FunctionTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObject* convertedMembers =
        converter.convertDict(mFreeVariableResolutions);
    if (convertedMembers == nullptr) {
        return nullptr;
        }

    PyObject* pyFileDescription = converter.convert(mSourceFileId);
    if (pyFileDescription == nullptr) {
        Py_DECREF(convertedMembers);
        return nullptr;
        }

    PyObject* tr = converter.rehydrator().instantiateFunction(
        pyFileDescription,
        mLinenumber,
        convertedMembers
        );

    Py_DECREF(pyFileDescription);
    Py_DECREF(convertedMembers);

    return tr;
    }
