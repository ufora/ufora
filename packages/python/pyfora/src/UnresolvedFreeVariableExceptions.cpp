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


UnresolvedFreeVariableExceptions::UnresolvedFreeVariableExceptions()
    {
    PyObjectPtr unresolvedFreeVariableExceptionsModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.UnresolvedFreeVariableExceptions"));
    if (unresolvedFreeVariableExceptionsModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mUnresolvedFreeVariableExceptionWithTraceClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule.get(),
            "UnresolvedFreeVariableExceptionWithTrace"
            )
        );
    if (mUnresolvedFreeVariableExceptionWithTraceClass == nullptr)
        {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mUnresolvedFreeVariableExceptionClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule.get(),
            "UnresolvedFreeVariableException"
            )
        );
    if (mUnresolvedFreeVariableExceptionClass == nullptr)
        {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    
    mGetUnresolvedFreeVariableExceptionWithTraceFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule.get(),
            "getUnresolvedFreeVariableExceptionWithTrace"
            )
        );
    if (mGetUnresolvedFreeVariableExceptionWithTraceFun == nullptr)
        {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTraceClass() const
    {
    return mUnresolvedFreeVariableExceptionWithTraceClass.get();
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionClass() const
    {
    return mUnresolvedFreeVariableExceptionClass.get();
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTrace(
        const PyObject* unresolvedFreeVariableException,
        const PyObject* filename
        ) const
    {
    return PyObject_CallFunctionObjArgs(
        mGetUnresolvedFreeVariableExceptionWithTraceFun.get(),
        unresolvedFreeVariableException,
        filename,
        nullptr
        );
    }
