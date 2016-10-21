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
#include "FreeVariableResolver.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


FreeVariableResolver::FreeVariableResolver(
        PyObject* exclude_list,
        PyObject* terminal_value_filter
        )
    : mPureFreeVariableResolver(0),
      exclude_list(exclude_list),
      terminal_value_filter(terminal_value_filter)
    {
    Py_INCREF(exclude_list);
    Py_INCREF(terminal_value_filter);
    _initPureFreeVariableResolver();
    }


FreeVariableResolver::~FreeVariableResolver()
    {
    Py_XDECREF(mPureFreeVariableResolver);
    Py_XDECREF(terminal_value_filter);
    Py_XDECREF(exclude_list);
    }


void FreeVariableResolver::_initPureFreeVariableResolver()
    {
    PyObject* freeVariableResolverModule = PyImport_ImportModule("pyfora.FreeVariableResolver");
    if (freeVariableResolverModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    
    PyObject* freeVariableResolverClass = PyObject_GetAttrString(
        freeVariableResolverModule,
        "FreeVariableResolver"
        );
    if (freeVariableResolverClass == nullptr) {
        Py_DECREF(freeVariableResolverModule);
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mPureFreeVariableResolver = PyObject_CallFunctionObjArgs(
        freeVariableResolverClass,
        exclude_list,
        terminal_value_filter,
        nullptr);
    if (mPureFreeVariableResolver == nullptr) {
        Py_DECREF(freeVariableResolverClass);
        Py_DECREF(freeVariableResolverModule);
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject* FreeVariableResolver::resolveFreeVariableMemberAccessChainsInAst(
        const PyObject* pyObject,
        const PyObject* pyAst,
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* convertedObjectCache) const
    {
    PyObject* resolveFreeVariableMemberAccessChainsInAstFun =
        PyObject_GetAttrString(mPureFreeVariableResolver,
                               "resolveFreeVariableMemberAccessChainsInAst");
    if (resolveFreeVariableMemberAccessChainsInAstFun == nullptr) {
        return nullptr;
        }
    
    PyObject* res = PyObject_CallFunctionObjArgs(
        resolveFreeVariableMemberAccessChainsInAstFun,
        pyObject,
        pyAst,
        freeMemberAccessChainsWithPositions,
        convertedObjectCache,
        nullptr);
    
    Py_DECREF(resolveFreeVariableMemberAccessChainsInAstFun);

    return res;
    }


PyObject* FreeVariableResolver::resolveFreeVariableMemberAccessChains(
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* boundVariables,
        const PyObject* convertedObjectCache) const
    {
    PyObject* resolveFreeVariableMemberAccessChainsFun = 
        PyObject_GetAttrString(
            mPureFreeVariableResolver,
            "resolveFreeVariableMemberAccessChains"
            );
    if (resolveFreeVariableMemberAccessChainsFun == nullptr) {
        return nullptr;
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        resolveFreeVariableMemberAccessChainsFun,
        freeMemberAccessChainsWithPositions,
        boundVariables,
        convertedObjectCache,
        nullptr);

    Py_DECREF(resolveFreeVariableMemberAccessChainsFun);

    return res;
    }
