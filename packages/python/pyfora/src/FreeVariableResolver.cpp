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


ResolutionResult::ResolutionResult(
    const PyObjectPtr& inResolvedChainsDict,
    const PyObjectPtr& inUnresolvedChainsSet
    ) :
        resolvedChainsDict(inResolvedChainsDict),
        unresolvedChainsSet(inUnresolvedChainsSet)
    {
    }


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


namespace {

ResolutionResult translateToResolutionResult(const PyObjectPtr& p)
    {
    if (p == nullptr) {
        throw std::runtime_error(
            "py error in FreeVariableResolver: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObject* rawPtr = p.get();
    if (not PyTuple_Check(rawPtr) or PyTuple_GET_SIZE(rawPtr) != 2)
        {
        throw std::runtime_error(
            "FreeVariableResolver::<anonymous namespace>::"
            "translateToResolutionResult expects a length-2 tuple"
            );
        }    
    if (not PyDict_Check(PyTuple_GET_ITEM(rawPtr, 0)))
        {
        throw std::runtime_error(
            "FreeVariableResolver::<anonymous namespace>::"
            "translateToResolutionResult expects a tuple of length 2 "
            "having a dict as its first argument"
            );
        }
    if (not PySet_Check(PyTuple_GET_ITEM(rawPtr, 1)))
        {
        throw std::runtime_error(
            "FreeVariableResolver::<anonymous namespace>::"
            "translateToResolutionResult expects a tuple of length 2 "
            "having a set as its second argument"
            );
        }

    return ResolutionResult(
        PyObjectPtr::incremented(PyTuple_GET_ITEM(rawPtr, 0)),
        PyObjectPtr::incremented(PyTuple_GET_ITEM(rawPtr, 1))
        );
    }

}


ResolutionResult FreeVariableResolver::resolveFreeVariableMemberAccessChainsInAst(
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
        throw std::runtime_error(
            "py error in FreeVariableResolver::"
            "resolveFreeVariableMemberAccessChainsInAst: " +
            PyObjectUtils::format_exc()
            );
        }
    
    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            resolveFreeVariableMemberAccessChainsInAstFun.get(),
            pyObject,
            pyAst,
            freeMemberAccessChainsWithPositions,
            convertedObjectCache,
            nullptr
            )
        );
    
    return translateToResolutionResult(res);
    }


ResolutionResult FreeVariableResolver::resolveFreeVariableMemberAccessChains(
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* boundVariables,
        const PyObject* convertedObjectCache) const
    {
    PyObjectPtr resolveFreeVariableMemberAccessChainsFun =
        PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                mPureFreeVariableResolver.get(),
                "resolveFreeVariableMemberAccessChains"
                )
            );
    if (resolveFreeVariableMemberAccessChainsFun == nullptr) {
        throw std::runtime_error(
            "py error in FreeVariableResolver::"
            "resolveFreeVariableMemberAccessChains: " +
            PyObjectUtils::format_exc()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            resolveFreeVariableMemberAccessChainsFun.get(),
            freeMemberAccessChainsWithPositions,
            boundVariables,
            convertedObjectCache,
            nullptr
            )
        );

    return translateToResolutionResult(res);
    }
