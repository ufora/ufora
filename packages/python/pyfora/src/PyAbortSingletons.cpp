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
#include "PyAbortSingletons.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


PyAbortSingletons::PyAbortSingletons()
    : mSingletonNameToObject(nullptr)
    {
    PyObject* pyAbortSingletonsModule = PyImport_ImportModule(
        "pyfora.PyAbortSingletons");
    if (pyAbortSingletonsModule == nullptr) {
        throw std::runtime_error(
            "py error creating (cpp) PyAbortSingletons: " +
            PyObjectUtils::exc_string()
            );
        }

    mSingletonNameToObject = PyObject_GetAttrString(
        pyAbortSingletonsModule,
        "singletonNameToObject"
        );

    if (mSingletonNameToObject == nullptr) {
        throw std::runtime_error(
            "py error creating (cpp) PyAbortSingletons: " +
            PyObjectUtils::exc_string()
            );
        }    
    }


PyAbortSingletons::PyAbortSingletons(const PyAbortSingletons& other)
    : mSingletonNameToObject(other.mSingletonNameToObject)
    {
    Py_INCREF(mSingletonNameToObject);
    }


PyAbortSingletons::~PyAbortSingletons()
    {
    Py_DECREF(mSingletonNameToObject);
    }


PyObject* PyAbortSingletons::singletonNameToObject(const std::string& name) const
    {
    PyObject* tr = PyDict_GetItemString(
        mSingletonNameToObject,
        name.c_str()
        );

    // borrowed reference, so we incref it
    Py_INCREF(tr);

    return tr;
    }
