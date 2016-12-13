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
#pragma once

#include <Python.h>

#include "core/PyObjectPtr.hpp"

#include <map>


class FreeVariableResolver {
public:
    FreeVariableResolver(
        const PyObjectPtr& exclude_list,
        const PyObjectPtr& terminal_value_filter
        );

    // returns a new reference to a dict: FVMAC -> (resolution, location)
    // FVMAC here is a tuple of strings
    PyObject* resolveFreeVariableMemberAccessChainsInAst(
        const PyObject* pyObject,
        const PyObject* pyAst,
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* convertedObjectCache) const;

    PyObject* resolveFreeVariableMemberAccessChains(
        const PyObject* freeMemberAccessChainsWithPositions,
        const PyObject* boundVariables,
        const PyObject* convertedObjectCache) const;

private:
    PyObjectPtr mPureFreeVariableResolver;
    PyObjectPtr mExcludeList;
    PyObjectPtr mTerminalValueFilter;

    FreeVariableResolver(const FreeVariableResolver&) = delete;
    void operator=(const FreeVariableResolver&) = delete;

    void _initPureFreeVariableResolver();

};

