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

#include <stdexcept>

#include "PyObjectUtils.hpp"


PureImplementationMappings::PureImplementationMappings(
       PyObject* pyPureImplementationMappings
       )
    : mPyPureImplementationMappings(pyPureImplementationMappings)
    {
    if (pyPureImplementationMappings == nullptr) {
        throw std::runtime_error(
            "can't pass a Null ptr to ctor of PureImplementationMappings");
        }

    Py_INCREF(mPyPureImplementationMappings);
    }


PureImplementationMappings::PureImplementationMappings(
        const PureImplementationMappings& mappings
        )
    : mPyPureImplementationMappings(mappings.mPyPureImplementationMappings)
    {
    Py_INCREF(mPyPureImplementationMappings);
    }


bool 
PureImplementationMappings::canInvertInstancesOf(const PyObject* classObject)
    {
    PyObject* canInvertInstancesOfFun = PyObject_GetAttrString(
        mPyPureImplementationMappings,
        "canInvertInstancesOf"
        );
    if (canInvertInstancesOfFun == nullptr) {
        throw std::runtime_error(
            "py err in PureImplementationMappings::canInvertInstancesOf: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        canInvertInstancesOfFun,
        classObject,
        nullptr
        );

    Py_DECREF(canInvertInstancesOfFun);

    int isTrue = PyObject_IsTrue(tr);

    Py_DECREF(tr);

    if (isTrue < 0) {
        throw std::runtime_error(
            "py error calling IsTrue on an object: " +
            PyObjectUtils::format_exc()
            );
        }

    return isTrue;
    }


PureImplementationMappings::~PureImplementationMappings()
    {
    Py_XDECREF(mPyPureImplementationMappings);
    }


PyObject* PureImplementationMappings::mappableInstanceToPure(
        const PyObject* pyObject)
    {
    PyObject* pyString = PyString_FromString("mappableInstanceToPure");
    if (pyString == nullptr) {
        return nullptr;
        }

    PyObject* pureInstance = PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings,
        pyString,
        pyObject,
        nullptr
        );

    Py_DECREF(pyString);

    if (pureInstance == nullptr) {
        return nullptr;
        }

    return pureInstance;
    }


bool PureImplementationMappings::canMap(const PyObject* pyObject)
    {
    PyObject* pyString = PyString_FromString("canMap");
    if (pyString == nullptr) {
        throw std::runtime_error(
            "py error in PureImplementationMappings::canMap: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings,
        pyString,
        pyObject,
        nullptr
        );

    Py_DECREF(pyString);

    if (res == nullptr) {
        throw std::runtime_error(
            "py error in PureImplementationMappings::canMap: " +
            PyObjectUtils::exc_string()
            );
        }

    int isTrue = PyObject_IsTrue(res);
    
    Py_DECREF(res);

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
    PyObject* methodName = PyString_FromString("pureInstanceToMappable");
    if (methodName == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings,
        methodName,
        instance,
        nullptr
        );

    Py_DECREF(methodName);;
    
    return tr;
    }


bool PureImplementationMappings::canInvert(const PyObject* pyObject)
    {
    PyObject* methodName = PyString_FromString("canInvert");
    if (methodName == nullptr) {
        throw std::runtime_error(
            "py error getting a py string from a C string: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObject* tr = PyObject_CallMethodObjArgs(
        mPyPureImplementationMappings,
        methodName,
        pyObject,
        nullptr
        );

    Py_DECREF(methodName);

    if (tr == nullptr) {
        throw std::runtime_error(
            "py error calling `canInvert`: " +
            PyObjectUtils::format_exc()
            );
        }

    int isTrue = PyObject_IsTrue(tr);

    Py_DECREF(tr);

    if (isTrue < 0) {
        throw std::runtime_error(
            "py error calling IsTrue on an object: " +
            PyObjectUtils::format_exc()
            );
        }

    return isTrue;
    }
