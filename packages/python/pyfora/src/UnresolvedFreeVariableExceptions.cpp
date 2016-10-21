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
#include "UnresolvedFreeVariableExceptions.hpp"

#include "PyObjectUtils.hpp"

#include <stdexcept>


UnresolvedFreeVariableExceptions::UnresolvedFreeVariableExceptions() :
    mUnresolvedFreeVariableExceptionWithTraceClass(nullptr),
    mUnresolvedFreeVariableExceptionClass(nullptr),
    mGetUnresolvedFreeVariableExceptionWithTraceFun(nullptr)
    {
    PyObject* unresolvedFreeVariableExceptionsModule = 
        PyImport_ImportModule("pyfora.UnresolvedFreeVariableExceptions");
    if (unresolvedFreeVariableExceptionsModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mUnresolvedFreeVariableExceptionWithTraceClass =
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule,
            "UnresolvedFreeVariableExceptionWithTrace"
            );
    if (mUnresolvedFreeVariableExceptionWithTraceClass == nullptr)
        {
        Py_DECREF(unresolvedFreeVariableExceptionsModule);
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mUnresolvedFreeVariableExceptionClass =
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule,
            "UnresolvedFreeVariableException"
            );
    if (mUnresolvedFreeVariableExceptionClass == nullptr)
        {
        Py_DECREF(unresolvedFreeVariableExceptionsModule);
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    
    mGetUnresolvedFreeVariableExceptionWithTraceFun =
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule,
            "getUnresolvedFreeVariableExceptionWithTrace"
            );
    if (mGetUnresolvedFreeVariableExceptionWithTraceFun == nullptr)
        {
        Py_DECREF(unresolvedFreeVariableExceptionsModule);
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    Py_DECREF(unresolvedFreeVariableExceptionsModule);
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTraceClass()
    {
    return _getInstance().mUnresolvedFreeVariableExceptionWithTraceClass;
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionClass()
    {
    return _getInstance().mUnresolvedFreeVariableExceptionClass;
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTrace(
        const PyObject* unresolvedFreeVariableException,
        const PyObject* filename
        )
    {
    return PyObject_CallFunctionObjArgs(
        _getInstance().mGetUnresolvedFreeVariableExceptionWithTraceFun,
        unresolvedFreeVariableException,
        filename,
        nullptr
        );
    }
