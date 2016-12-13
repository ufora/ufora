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


PyforaInspect::PyforaInspect()
    {
    _initMembers();
    }


void PyforaInspect::_initMembers()
    {
    PyObjectPtr typesModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("types"));
    if (typesModule == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mClassType = PyObjectPtr::unincremented(
        PyObject_GetAttrString(typesModule.get(), "ClassType"));
    if (mClassType == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mTypeType = PyObjectPtr::unincremented(
        PyObject_GetAttrString(typesModule.get(), "TypeType"));
    if (mTypeType == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mFunctionType = PyObjectPtr::unincremented(
        PyObject_GetAttrString(typesModule.get(), "FunctionType"));
    if (mFunctionType == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mModuleType = PyObjectPtr::unincremented(
        PyObject_GetAttrString(typesModule.get(), "ModuleType"));
    if (mModuleType == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    PyObjectPtr pyforaInspectModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.PyforaInspect"));
    if (pyforaInspectModule == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mGetLinesFunc = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyforaInspectModule.get(), "getlines"));
    if (mGetLinesFunc == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }

    mPyforaInspectErrorClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyforaInspectModule.get(),
            "PyforaInspectError"
            ));
    if (mPyforaInspectErrorClass == nullptr) {
        throw std::runtime_error(
            "py err in PyforaInspect::_initMembers: " + PyObjectUtils::format_exc()
            );
        }
    }


bool PyforaInspect::isclass(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mTypeType.get()) or 
        PyObject_IsInstance(pyObject, mClassType.get());
    }


bool PyforaInspect::isclassinstance(PyObject* pyObject) const
    {
    return PyObject_HasAttrString(pyObject, "__class__");
    }


bool PyforaInspect::isfunction(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mFunctionType.get());
    }


bool PyforaInspect::ismodule(PyObject* pyObject) const
    {
    return PyObject_IsInstance(pyObject, mModuleType.get());
    }


PyObject* PyforaInspect::getlines(const PyObject* obj) const
    {
    return PyObject_CallFunctionObjArgs(mGetLinesFunc.get(), obj, nullptr);
    }


PyObject* PyforaInspect::getPyforaInspectErrorClass() const {
    return mPyforaInspectErrorClass.get();
    }
