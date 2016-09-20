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

#include <stdexcept>


Ast::Ast() :
    mAstModule(0)
    {
    mAstModule = PyImport_ImportModule("ast");

    if (mAstModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import ast module");
        }
    }


PyObject* Ast::FunctionDef(PyObject* args, PyObject* kw)
    {
    PyObject* FunctionDefFun = PyObject_GetAttrString(
        _getInstance().mAstModule,
        "FunctionDef"
        );
    if (FunctionDefFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `FunctionDef` attr from ast module");
        }

    PyObject* res = PyObject_Call(FunctionDefFun, args, kw);

    Py_DECREF(FunctionDefFun);

    return res;
    }


PyObject* Ast::arguments(PyObject* args, PyObject* kw)
    {
    PyObject* argumentsFun = PyObject_GetAttrString(
        _getInstance().mAstModule,
        "arguments"
        );
    if (argumentsFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `arguments` attr from ast module");
        }

    PyObject* res = PyObject_Call(argumentsFun, args, kw);

    Py_DECREF(argumentsFun);

    return res;
    }
