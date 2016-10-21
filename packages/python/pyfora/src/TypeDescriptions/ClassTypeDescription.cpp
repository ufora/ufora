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
#include "../PyObjectUtils.hpp"
#include "../PythonObjectRehydrator.hpp"
#include "ClassTypeDescription.hpp"

#include <stdexcept>


ClassTypeDescription::ClassTypeDescription(
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions,
        const std::vector<int64_t>& baseClassIds
    ) :
        mSourceFileId(sourceFileId),
        mLinenumber(linenumber),
        mFreeVariableResolutions(freeVariableResolutions),
        mBaseClassIds(baseClassIds)
    {
    if (mFreeVariableResolutions == nullptr) {
        throw std::runtime_error(
            "got a nullptr freeVariableResolutions arg in "
            "ClassTypeDescription::ClassTypeDescription"
            );
        }
    if (not PyDict_Check(freeVariableResolutions)) {
        Py_DECREF(freeVariableResolutions);
        throw std::runtime_error(
            "freeVariableResolutions arg in "
            "ClassTypeDescription::ClassTypeDescription "
            "must be a dict"
            );
        }

    Py_INCREF(mFreeVariableResolutions);
    }


ClassTypeDescription::~ClassTypeDescription()
    {
    Py_DECREF(mFreeVariableResolutions);
    }


PyObject* ClassTypeDescription::transform(
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

    PyObject* tr = converter.rehydrator().createClassObject(
        pyFileDescription,
        mLinenumber,
        convertedMembers
        );

    Py_DECREF(pyFileDescription);
    Py_DECREF(convertedMembers);

    return tr;
    }
