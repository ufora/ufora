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
#include "../core/PyObjectPtr.hpp"
#include "InstanceMethodTypeDescription.hpp"


InstanceMethodTypeDescription::InstanceMethodTypeDescription(
        int64_t instanceId,
        const std::string& methodName
        )
    : mInstanceId(instanceId),
      mMethodName(methodName)
    {
    }


PyObject* InstanceMethodTypeDescription::transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObjectPtr instance = PyObjectPtr::unincremented(c.convert(mInstanceId));
    if (instance == nullptr) {
        return nullptr;
        }

    return PyObject_GetAttrString(
        instance.get(),
        mMethodName.c_str()
        );
    }
