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
        const PyObjectPtr& exclude_list,
        const PyObjectPtr& terminal_value_filter
        )
    : mExcludeList(exclude_list),
      mTerminalValueFilter(terminal_value_filter)
    {
    _initPureFreeVariableResolver();
    }


void FreeVariableResolver::_initPureFreeVariableResolver()
    {
    PyObjectPtr freeVariableResolverModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.FreeVariableResolver"));
    if (freeVariableResolverModule == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    
    PyObjectPtr freeVariableResolverClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            freeVariableResolverModule.get(),
            "FreeVariableResolver"
            ));
    if (freeVariableResolverClass == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mPureFreeVariableResolver = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            freeVariableResolverClass.get(),
            mExcludeList.get(),
            mTerminalValueFilter.get(),
            nullptr));
    if (mPureFreeVariableResolver == nullptr) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }


PyObject* FreeVariableResolver::resolveFreeVariableMemberAccessChainsInAst(
        const PyObject* pyObject,
        const PyObject* pyAst,
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* convertedObjectCache) const
    {
    PyObjectPtr resolveFreeVariableMemberAccessChainsInAstFun =
        PyObjectPtr::unincremented(
            PyObject_GetAttrString(mPureFreeVariableResolver.get(),
                "resolveFreeVariableMemberAccessChainsInAst"));
    if (resolveFreeVariableMemberAccessChainsInAstFun == nullptr) {
        return nullptr;
        }
    
    return PyObject_CallFunctionObjArgs(
        resolveFreeVariableMemberAccessChainsInAstFun.get(),
        pyObject,
        pyAst,
        freeMemberAccessChainsWithPositions,
        convertedObjectCache,
        nullptr);
    }


PyObject* FreeVariableResolver::resolveFreeVariableMemberAccessChains(
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* boundVariables,
        const PyObject* convertedObjectCache) const
    {
    PyObjectPtr resolveFreeVariableMemberAccessChainsFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPureFreeVariableResolver.get(),
            "resolveFreeVariableMemberAccessChains"
            ));
    if (resolveFreeVariableMemberAccessChainsFun == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        resolveFreeVariableMemberAccessChainsFun.get(),
        freeMemberAccessChainsWithPositions,
        boundVariables,
        convertedObjectCache,
        nullptr);
    }
