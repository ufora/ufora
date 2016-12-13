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


Ast::Ast() 
    : mAstModule(PyObjectPtr::unincremented(PyImport_ImportModule("ast")))
    {
    if (mAstModule == nullptr) {
        throw std::runtime_error(
            "py error in Ast::get(): " + PyObjectUtils::format_exc()
            );
        }
    }


PyObject* Ast::FunctionDef(PyObject* args, PyObject* kw) const
    {
    PyObjectPtr FunctionDefFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mAstModule.get(),
            "FunctionDef"
            ));
    if (FunctionDefFun == nullptr) {
        return nullptr;
        }

    return PyObject_Call(FunctionDefFun.get(), args, kw);
    }


PyObject* Ast::arguments(PyObject* args, PyObject* kw) const
    {
    PyObjectPtr argumentsFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mAstModule.get(),
            "arguments"
            ));
    if (argumentsFun == nullptr) {
        return nullptr;
        }

    return PyObject_Call(argumentsFun.get(), args, kw);
    }
