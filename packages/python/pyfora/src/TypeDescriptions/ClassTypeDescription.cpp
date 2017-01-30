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
        mBaseClassIds(baseClassIds)
    {
    if (freeVariableResolutions == nullptr) {
        throw std::runtime_error(
            "got a nullptr freeVariableResolutions arg in "
            "ClassTypeDescription::ClassTypeDescription"
            );
        }
    if (not PyDict_Check(freeVariableResolutions)) {
        throw std::runtime_error(
            "freeVariableResolutions arg in "
            "ClassTypeDescription::ClassTypeDescription "
            "must be a dict"
            );
        }

    mFreeVariableResolutions = PyObjectPtr::incremented(freeVariableResolutions);
    }


PyObject* ClassTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObjectPtr convertedMembers = PyObjectPtr::unincremented(
        converter.convertDict(mFreeVariableResolutions.get()));
    if (convertedMembers == nullptr) {
        return nullptr;
        }
    
    PyObjectPtr pyFileDescription = PyObjectPtr::unincremented(
        converter.convert(mSourceFileId));
    if (pyFileDescription == nullptr) {
        return nullptr;
        }

    return converter.rehydrator().createClassObject(
        pyFileDescription.get(),
        mLinenumber,
        convertedMembers.get()
        );
    }
