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
    : mJsonModule(PyObjectPtr::unincremented(PyImport_ImportModule("json")))
    {    
    if (mJsonModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject* Json::loads(const std::string& s) {
    PyObjectPtr loadsFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mJsonModule.get(), "loads"));
    if (loadsFun == nullptr) {
        return nullptr;
        }

    PyObjectPtr pyString = PyObjectPtr::unincremented(
        PyString_FromStringAndSize(s.data(), s.size()));
    if (pyString == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        loadsFun.get(),
        pyString.get(),
        nullptr);
    }


std::string Json::dumps(const PyObject* obj)
    {
    PyObjectPtr dumpsFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mJsonModule.get(), "dumps"));
    if (dumpsFun == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            dumpsFun.get(),
            obj,
            nullptr
            )
        );
    if (res == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    if (not PyString_Check(res.get())) {
        throw std::runtime_error("expected json.dumps to return a string");
        }

    return std::string(
        PyString_AS_STRING(res.get()),
        PyString_GET_SIZE(res.get())
        );
    }
