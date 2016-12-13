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

#include "core/PyObjectPtr.hpp"


class PyforaInspect {
public:
    PyforaInspect();

    bool isclass(PyObject*) const;
    bool isclassinstance(PyObject*) const;
    bool isfunction(PyObject*) const;
    bool ismodule(PyObject*) const;

    PyObject* getlines(const PyObject*) const;

    // returns a borrowed reference
    PyObject* getPyforaInspectErrorClass() const;

private:
    void operator=(const PyforaInspect&) = delete;

    void _initMembers();

    PyObjectPtr mClassType;
    PyObjectPtr mTypeType;
    PyObjectPtr mFunctionType;
    PyObjectPtr mModuleType;
    PyObjectPtr mGetLinesFunc;
    PyObjectPtr mPyforaInspectErrorClass;
};
