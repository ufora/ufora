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
#include "NamedSingletons.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


NamedSingletons::NamedSingletons()
    : mSingletonNameToObjectDict(nullptr)
    {
    PyObject* namedSingletonsModule = PyImport_ImportModule("pyfora.NamedSingletons");
    if (namedSingletonsModule == nullptr) {
        throw std::runtime_error(
            "error getting pyfora.NamedSingletons: " +
            PyObjectUtils::exc_string()
            );
        }

    mSingletonNameToObjectDict = PyObject_GetAttrString(
        namedSingletonsModule,
        "singletonNameToObject");
    if (mSingletonNameToObjectDict == nullptr) {
        throw std::runtime_error(
            "error getting pyfora.NamedSingletons.singletonNameToObject: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyDict_Check(mSingletonNameToObjectDict)) {
        Py_DECREF(mSingletonNameToObjectDict);
        throw std::runtime_error(
            "expected pyfora.NamedSingletons.singletonNameToObject "
            " to be a dict"
            );
        }
    }


PyObject* NamedSingletons::singletonNameToObject(const std::string& s)
    {
    PyObject* tr = PyDict_GetItemString(
        _getInstance().mSingletonNameToObjectDict,
        s.c_str()
        );

    // borrowed reference, so we incref it
    Py_INCREF(tr);

    return tr;
    }
