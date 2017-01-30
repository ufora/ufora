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
#include "../core/PyObjectPtr.hpp"
#include "FunctionTypeDescription.hpp"

#include <stdexcept>


FunctionTypeDescription::FunctionTypeDescription(
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions
    ) :
        mSourceFileId(sourceFileId),
        mLinenumber(linenumber)
    {
    mFreeVariableResolutions = PyObjectPtr::incremented(freeVariableResolutions);
    }


PyObject* FunctionTypeDescription::transform(
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

    return converter.rehydrator().instantiateFunction(
        pyFileDescription.get(),
        mLinenumber,
        convertedMembers.get()
        );
    }
