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
#include "PureImplementationMappings.hpp"

#include <iostream>
#include <stdexcept>

#include "PyObjectUtils.hpp"


PureImplementationMappings::PureImplementationMappings(
       const PyObjectPtr& pyPureImplementationMappings
       )
    : mPyPureImplementationMappings(pyPureImplementationMappings)
    {
    }


bool 
PureImplementationMappings::canInvertInstancesOf(const PyObject* classObject)
    {
    PyObjectPtr canInvertInstancesOfFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyPureImplementationMappings.get(),
            "canInvertInstancesOf"
            ));
    if (canInvertInstancesOfFun == nullptr) {
        throw std::runtime_error(
            "py err in PureImplementationMappings::canInvertInstancesOf: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            canInvertInstancesOfFun.get(),
            classObject,
            nullptr
            ));

    int isTrue = PyObject_IsTrue(res.get());

    if (isTrue < 0) {
        throw std::runtime_error(
            "py error calling IsTrue on an object: " +
            PyObjectUtils::format_exc()
            );
        }

    return isTrue;
    }


PyObject* PureImplementationMappings::mappableInstanceToPure(
        const PyObject* pyObject)
    {
    PyObjectPtr pyString = PyObjectPtr::unincremented(
        PyString_FromString("mappableInstanceToPure"));
    if (pyString == nullptr) {
        return nullptr;
        }

    return PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings.get(),
        pyString.get(),
        pyObject,
        nullptr
        );
    }


bool PureImplementationMappings::canMap(const PyObject* pyObject)
    {
    PyObjectPtr pyString = PyObjectPtr::unincremented(
        PyString_FromString("canMap"));
    if (pyString == nullptr) {
        throw std::runtime_error(
            "py error in PureImplementationMappings::canMap: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallMethodObjArgs(
            mPyPureImplementationMappings.get(),
            pyString.get(),
            pyObject,
            nullptr
            )
        );

    if (res == nullptr) {
        throw std::runtime_error(
            "py error in PureImplementationMappings::canMap: " +
            PyObjectUtils::exc_string()
            );
        }

    int isTrue = PyObject_IsTrue(res.get());

    if (isTrue < 0) {
        throw std::runtime_error(
            "py error calling IsTrue: " + PyObjectUtils::format_exc()            
            );
        }
    
    return isTrue;
    }


PyObject* PureImplementationMappings::pureInstanceToMappable(
        const PyObject* instance
        )
    {
    PyObjectPtr methodName = PyObjectPtr::unincremented(
        PyString_FromString("pureInstanceToMappable"));
    if (methodName == nullptr) {
        return nullptr;
        }

    return PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings.get(),
        methodName.get(),
        instance,
        nullptr
        );
    }


bool PureImplementationMappings::canInvert(const PyObject* pyObject)
    {
    PyObjectPtr methodName = PyObjectPtr::unincremented(
        PyString_FromString("canInvert"));
    if (methodName == nullptr) {
        throw std::runtime_error(
            "py error getting a py string from a C string: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallMethodObjArgs(
            mPyPureImplementationMappings.get(),
            methodName.get(),
            pyObject,
            nullptr
            )
        );

    if (res == nullptr) {
        throw std::runtime_error(
            "py error calling `canInvert`: " +
            PyObjectUtils::format_exc()
            );
        }

    int isTrue = PyObject_IsTrue(res.get());

    if (isTrue < 0) {
        throw std::runtime_error(
            "py error calling IsTrue on an object: " +
            PyObjectUtils::format_exc()
            );
        }

    return isTrue;
    }
