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
#include "Ast.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


Ast::Ast(const Ast& other)
    : mAstModule(other.mAstModule)
    {
    Py_INCREF(mAstModule);
    }


Ast::~Ast()
    {
    Py_XDECREF(mAstModule);
    }


Ast::Ast() : mAstModule(nullptr)
    {
    mAstModule = PyImport_ImportModule("ast");

    if (mAstModule == nullptr) {
        throw std::runtime_error(
            "py error in Ast::get(): " + PyObjectUtils::format_exc()
            );
        }
    }


PyObject* Ast::FunctionDef(PyObject* args, PyObject* kw) const
    {
    PyObject* FunctionDefFun = PyObject_GetAttrString(
        mAstModule,
        "FunctionDef"
        );
    if (FunctionDefFun == nullptr) {
        return nullptr;
        }

    PyObject* res = PyObject_Call(FunctionDefFun, args, kw);

    Py_DECREF(FunctionDefFun);

    return res;
    }


PyObject* Ast::arguments(PyObject* args, PyObject* kw) const
    {
    PyObject* argumentsFun = PyObject_GetAttrString(
        mAstModule,
        "arguments"
        );
    if (argumentsFun == nullptr) {
        return nullptr;
        }

    PyObject* res = PyObject_Call(argumentsFun, args, kw);

    Py_DECREF(argumentsFun);

    return res;
    }
