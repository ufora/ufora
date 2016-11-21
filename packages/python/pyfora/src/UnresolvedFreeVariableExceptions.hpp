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
#pragma once

#include <Python.h>

#include <string>


class UnresolvedFreeVariableExceptions {
public:
    UnresolvedFreeVariableExceptions();
    ~UnresolvedFreeVariableExceptions();
    UnresolvedFreeVariableExceptions(
        const UnresolvedFreeVariableExceptions&
        );

    // returns a borrowed reference
    PyObject* getUnresolvedFreeVariableExceptionWithTraceClass() const;
    // returns a borrowed reference
    PyObject* getUnresolvedFreeVariableExceptionClass() const;

    // returns a new reference
    PyObject* getUnresolvedFreeVariableExceptionWithTrace(
        const PyObject* unresolvedFreeVariableException,
        const PyObject* filename
        ) const;
    
private:
    void operator=(const UnresolvedFreeVariableExceptions&) = delete;

    PyObject* mUnresolvedFreeVariableExceptionWithTraceClass;
    PyObject* mUnresolvedFreeVariableExceptionClass;
    PyObject* mGetUnresolvedFreeVariableExceptionWithTraceFun;

};
