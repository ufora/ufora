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
#include "ClassInstanceTypeDescription.hpp"

#include <stdexcept>


ClassInstanceTypeDescription::ClassInstanceTypeDescription(
        int64_t classId,
        const std::map<std::string, int64_t>& classMembers)
    : mClassId(classId),
      mClassMembers(classMembers)
    {
    }


PyObject* ClassInstanceTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObjectPtr classObject = PyObjectPtr::unincremented(
        converter.convert(mClassId));
    if (classObject == nullptr) {
        return nullptr;
        }

    if (converter.rehydrator().pureImplementationMappings()
        .canInvertInstancesOf(classObject.get()))
        {
        PyObjectPtr members = PyObjectPtr::unincremented(
            converter.convertDict(mClassMembers, true));
        if (members == nullptr) {
            return nullptr;
            }

        PyObjectPtr pureInstance = PyObjectPtr::unincremented(
            converter.rehydrator().instantiateClass(
                classObject.get(),
                members.get()
                )
            );

        if (pureInstance == nullptr) {
            return nullptr;
            }

        return converter.rehydrator()
            .pureImplementationMappings()
            .pureInstanceToMappable(pureInstance.get());
        }
    else {
        PyObjectPtr members = PyObjectPtr::unincremented(
            converter.convertDict(mClassMembers, false));

        PyObjectPtr instance = PyObjectPtr::unincremented(
            converter.rehydrator().instantiateClass(
                classObject.get(),
                members.get()
                )
            );

        if (instance == nullptr) {
            return nullptr;
            }

        return converter.rehydrator()
            .invertPureClassInstanceIfNecessary(instance.get());
        }

    throw std::runtime_error(
        "ClassInstanceTypeDescription::transform not implemented"
        );
    }


PyObject* ClassInstanceTypeDescription::_convertMembers(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    return converter.convertDict(mClassMembers,
                                 retainHomogenousListsAsNumpy);
    }
