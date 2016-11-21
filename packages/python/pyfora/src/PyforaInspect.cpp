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
#include "PyforaInspect.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


PyforaInspect::PyforaInspect(const PyforaInspect& other) :
        mClassType(other.mClassType),
        mTypeType(other.mTypeType),
        mFunctionType(other.mFunctionType),
        mModuleType(other.mModuleType),
        mGetLinesFunc(other.mGetLinesFunc),
        mPyforaInspectErrorClass(other.mPyforaInspectErrorClass)
    {
    Py_INCREF(mClassType);
    Py_INCREF(mTypeType);
    Py_INCREF(mFunctionType);
    Py_INCREF(mModuleType);
    Py_INCREF(mGetLinesFunc);
    Py_INCREF(mPyforaInspectErrorClass);
    }

PyforaInspect::PyforaInspect() :
        mClassType(nullptr),
        mTypeType(nullptr),
        mFunctionType(nullptr),
        mModuleType(nullptr),
        mGetLinesFunc(nullptr),
        mPyforaInspectErrorClass(nullptr)
    {
    _initMembers();
    }


PyforaInspect::~PyforaInspect()
    {
    Py_XDECREF(mPyforaInspectErrorClass);
    Py_XDECREF(mGetLinesFunc);
    Py_XDECREF(mModuleType);
    Py_XDECREF(mFunctionType);
    Py_XDECREF(mTypeType);
    Py_XDECREF(mClassType);
    }


void PyforaInspect::_initMembers()
    {
    PyObject* typesModule = PyImport_ImportModule("types");
    if (typesModule == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mClassType = PyObject_GetAttrString(typesModule, "ClassType");
    if (mClassType == nullptr) {
        Py_DECREF(typesModule);
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mTypeType = PyObject_GetAttrString(typesModule, "TypeType");
    if (mTypeType == nullptr) {
        Py_DECREF(typesModule);
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mFunctionType = PyObject_GetAttrString(typesModule, "FunctionType");
    if (mFunctionType == nullptr) {
        Py_DECREF(typesModule);
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mModuleType = PyObject_GetAttrString(typesModule, "ModuleType");
    if (mModuleType == nullptr) {
        Py_DECREF(typesModule);
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    Py_DECREF(typesModule);

    PyObject* pyforaInspectModule = PyImport_ImportModule("pyfora.PyforaInspect");
    if (pyforaInspectModule == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mGetLinesFunc = PyObject_GetAttrString(pyforaInspectModule, "getlines");
    if (mGetLinesFunc == nullptr) {
        Py_DECREF(pyforaInspectModule);
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mPyforaInspectErrorClass = PyObject_GetAttrString(
        pyforaInspectModule,
        "PyforaInspectError"
        );
    Py_DECREF(pyforaInspectModule);
    if (mPyforaInspectErrorClass == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }
    }


bool PyforaInspect::isclass(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mTypeType) or 
        PyObject_IsInstance(pyObject, mClassType);
    }


bool PyforaInspect::isclassinstance(PyObject* pyObject) const
    {
    return PyObject_HasAttrString(pyObject, "__class__");
    }


bool PyforaInspect::isfunction(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mFunctionType);
    }


bool PyforaInspect::ismodule(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mModuleType);
    }


PyObject* PyforaInspect::getlines(const PyObject* obj) const
    {
    return PyObject_CallFunctionObjArgs(mGetLinesFunc, obj, nullptr);
    }


PyObject* PyforaInspect::getPyforaInspectErrorClass() const {
    return mPyforaInspectErrorClass;
    }
