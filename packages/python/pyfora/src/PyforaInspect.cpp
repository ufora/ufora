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

#include <stdexcept>


PyforaInspect::PyforaInspect() :
        mClassType(NULL),
        mTypeType(NULL),
        mFunctionType(NULL),
        mModuleType(NULL),
        mPyforaModule(NULL),
        mPyforaInspectModule(NULL),
        mGetLinesFunc(NULL),
        mPyforaInspectErrorClass(NULL)
    {
    _initMembers();
    }


void PyforaInspect::_initMembers()
    {
    PyObject* typesModule = PyImport_ImportModule("types");
    if (typesModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import types module");
        }

    mClassType = PyObject_GetAttrString(typesModule, "ClassType");
    if (mClassType == NULL) {
        PyErr_Print();
        Py_DECREF(typesModule);
        throw std::runtime_error("couldn't get ClassType member in types module");
        }

    mTypeType = PyObject_GetAttrString(typesModule, "TypeType");
    if (mTypeType == NULL) {
        PyErr_Print();
        Py_DECREF(typesModule);
        throw std::runtime_error("couldn't get TypeType member in types module");
        }

    mFunctionType = PyObject_GetAttrString(typesModule, "FunctionType");
    if (mFunctionType == NULL) {
        PyErr_Print();
        Py_DECREF(typesModule);
        throw std::runtime_error("couldn't get FunctionType member in types module");
        }

    mModuleType = PyObject_GetAttrString(typesModule, "ModuleType");
    if (mModuleType == NULL) {
        PyErr_Print();
        Py_DECREF(typesModule);
        throw std::runtime_error("couldn't get ModuleType member in types module");
        }

    Py_DECREF(typesModule);

    mPyforaModule = PyImport_ImportModule("pyfora");

    if (mPyforaModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import pyfora module");
        }
    mPyforaInspectModule = PyObject_GetAttrString(mPyforaModule,
                                                  "PyforaInspect");
    if (mPyforaInspectModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import pyfora.PyforaInspect");
        }

    mGetLinesFunc = PyObject_GetAttrString(mPyforaInspectModule,
                                           "getlines");
    if (mGetLinesFunc == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't find `getlines` func in pyfora.PyforaInspect");
        }

    mPyforaInspectErrorClass = PyObject_GetAttrString(
        mPyforaInspectModule,
        "PyforaInspectError"
        );

    if (mPyforaInspectErrorClass == NULL) {
        throw std::runtime_error(
            "couldn't get PyforaInspectError class"
            );
        }
    }


bool PyforaInspect::isclass(PyObject* pyObject)
    {
    return PyObject_IsInstance(pyObject, _getInstance().mTypeType) or 
        PyObject_IsInstance(pyObject, _getInstance().mClassType);
    }


bool PyforaInspect::isclassinstance(PyObject* pyObject)
    {
    return PyObject_HasAttrString(pyObject, "__class__");
    }


bool PyforaInspect::isfunction(PyObject* pyObject)
    {
    return PyObject_IsInstance(pyObject, _getInstance().mFunctionType);
    }


bool PyforaInspect::ismodule(PyObject* pyObject)
    {
    return PyObject_IsInstance(pyObject, _getInstance().mModuleType);
    }


PyObject* PyforaInspect::getlines(const PyObject* obj)
    {
    return PyObject_CallFunctionObjArgs(_getInstance().mGetLinesFunc, obj, NULL);
    }


PyObject* PyforaInspect::getPyforaInspectErrorClass() {
    return _getInstance().mPyforaInspectErrorClass;
    }
