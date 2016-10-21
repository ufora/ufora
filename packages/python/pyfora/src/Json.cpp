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
#include "Json.hpp"

#include "PyObjectUtils.hpp"

#include <stdexcept>


Json::Json()
    : mJsonModule(nullptr)
    {
    mJsonModule = PyImport_ImportModule("json");
    if (mJsonModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject* Json::loads(const std::string& s) {
    PyObject* loadsFun = PyObject_GetAttrString(
        _getInstance().mJsonModule,
        "loads");
    if (loadsFun == nullptr) {
        return nullptr;
        }

    PyObject* pyString = PyString_FromStringAndSize(s.data(), s.size());
    if (pyString == nullptr) {
        Py_DECREF(loadsFun);
        return nullptr;
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        loadsFun,
        pyString,
        nullptr);
    
    Py_DECREF(pyString);
    Py_DECREF(loadsFun);

    return res;
    }


std::string Json::dumps(const PyObject* obj)
    {
    PyObject* dumpsFun = PyObject_GetAttrString(
        _getInstance().mJsonModule,
        "dumps");
    if (dumpsFun == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        dumpsFun,
        obj,
        nullptr
        );
    
    Py_DECREF(dumpsFun);

    if (res == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    if (not PyString_Check(res)) {
        Py_DECREF(res);
        throw std::runtime_error("expected json.dumps to return a string");
        }

    std::string tr = std::string(
        PyString_AS_STRING(res),
        PyString_GET_SIZE(res)
        );

    Py_DECREF(res);

    return tr;
    }
