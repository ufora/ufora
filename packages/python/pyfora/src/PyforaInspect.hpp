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


class PyforaInspect {
public:
    static bool isclass(PyObject*);
    static bool isclassinstance(PyObject*);
    static bool isfunction(PyObject*);
    static bool ismodule(PyObject*);

    static PyObject* getlines(const PyObject*);

    // returns a borrowed reference
    static PyObject* getPyforaInspectErrorClass();

private:
    static PyforaInspect& _getInstance() {
        static PyforaInspect instance;
        return instance;
        }

    // implement, but keep private for singleton
    PyforaInspect();

    // declare private and don't implement these to prevent copying
    PyforaInspect(const PyforaInspect&);
    void operator=(const PyforaInspect&);

    void _initMembers();

    PyObject* mClassType;
    PyObject* mTypeType;
    PyObject* mFunctionType;
    PyObject* mModuleType;
    PyObject* mPyforaModule;
    PyObject* mPyforaInspectModule;
    PyObject* mGetLinesFunc;
    PyObject* mPyforaInspectErrorClass;
};
