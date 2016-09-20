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


UnresolvedFreeVariableExceptions::UnresolvedFreeVariableExceptions() :
    mUnresolvedFreeVariableExceptionWithTraceClass(NULL),
    mGetUnresolvedFreeVariableExceptionWithTraceFun(NULL)
    {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    if (pyforaModule == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    PyObject* unresolvedFreeVariableExceptionsModule = 
        PyObject_GetAttrString(
            pyforaModule,
            "UnresolvedFreeVariableExceptions"
            );

    Py_DECREF(pyforaModule);

    if (unresolvedFreeVariableExceptionsModule == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mUnresolvedFreeVariableExceptionWithTraceClass =
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule,
            "UnresolvedFreeVariableExceptionWithTrace"
            );

    if (unresolvedFreeVariableExceptionWithTraceClass == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mGetUnresolvedFreeVariableExceptionWithTraceFun =
        PyObject_GetAttrString(
            unresolvedFreeVariableExceptionsModule,
            "getUnresolvedFreeVariableExceptionWithTrace"
            );
    if (mGetUnresolvedFreeVariableExceptionWithTraceFun == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTraceClass()
    {
    Py_INCREF(mUnresolvedFreeVariableExceptionWithTraceClass);
    return mUnresolvedFreeVariableExceptionWithTraceClass;
    }


PyObject*
UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTrace(
        const PyObject* unresolvedFreeVariableException,
        const std::string& filename
        )
    {
    PyObject* pyFilename = PyString_FromStringAndSize(
        filename.data(),
        filename.size()
        );
    if (pyFilename == NULL) {
        return NULL;
        }
    
    PyObject* res = PyObject_CallFunctionObjArgs(
        mUnresolvedFreeVariableExceptionWithTraceClass,
        unresolvedFreeVariableException,
        pyFilename
        );

    Py_DECREF(pyFilename);
    
    return res;
    }
