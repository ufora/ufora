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


class PyAstFreeVariableAnalyses {
public:
    PyAstFreeVariableAnalyses();
    PyAstFreeVariableAnalyses(const PyAstFreeVariableAnalyses&);
    ~PyAstFreeVariableAnalyses();

    PyObject* getFreeMemberAccessChainsWithPositions(
        const PyObject* pyAst,
        bool isClassContext,
        bool getPositions,
        const PyObject* exclude_predicate) const;

    // should return a PySet
    PyObject* collectBoundValuesInScope(
        const PyObject* pyAst,
        bool getPositions=false) const;

    PyObject* varWithPosition(const PyObject* var, const PyObject* pos) const;

private:
    void operator=(const PyAstFreeVariableAnalyses&) = delete;

    void _initPyAstFreeVariableAnalysesModule();
    void _initGetFreeVariableMemberAccessChainsFun();
    void _initVarWithPosition();

    PyObject* mPyAstFreeVariableAnalysesModule;
    PyObject* mGetFreeVariableMemberAccessChainsFun;
    PyObject* mVarWithPosition;
    };
