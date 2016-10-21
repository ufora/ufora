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
#include "ClassInstanceTypeDescription.hpp"

#include <stdexcept>


ClassInstanceTypeDescription::ClassInstanceTypeDescription(
        int64_t classId,
        const std::map<std::string, int64_t>& classMembers)
    : mClassId(classId),
      mClassMembers(classMembers)
    {
    }


ClassInstanceTypeDescription::~ClassInstanceTypeDescription()
    {
    }


PyObject* ClassInstanceTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObject* classObject = converter.convert(mClassId);
    if (classObject == nullptr) {
        return nullptr;
        }

    if (converter.rehydrator().pureImplementationMappings()
            .canInvertInstancesOf(classObject))
        {
        PyObject* members = converter.convertDict(mClassMembers, true);
        if (members == nullptr) {
            Py_DECREF(classObject);
            return nullptr;
            }

        PyObject* pureInstance =
            converter.rehydrator().instantiateClass(
                classObject,
                members
                );

        Py_DECREF(members);
        Py_DECREF(classObject);

        if (pureInstance == nullptr) {
            return nullptr;
            }

        PyObject* tr = converter.rehydrator()
            .pureImplementationMappings()
            .pureInstanceToMappable(pureInstance);

        Py_DECREF(pureInstance);

        return tr;
        }
    else {
        PyObject* members = converter.convertDict(mClassMembers, false);

        PyObject* instance =
            converter.rehydrator().instantiateClass(
                classObject,
                members
                );

        Py_DECREF(members);
        Py_DECREF(classObject);

        if (instance == nullptr) {
            return nullptr;
            }

        PyObject* tr = converter.rehydrator()
            .invertPureClassInstanceIfNecessary(instance);

        Py_DECREF(instance);

        return tr;
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
