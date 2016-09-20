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
    static PyObject*  getFreeMemberAccessChainsWithPositions(
        const PyObject* pyAst,
        bool isClassContext,
        bool getPositions,
        const PyObject* exclude_predicate);

    // should return a PySet
    static PyObject* collectBoundValuesInScope(
        const PyObject* pyAst,
        bool getPositions=false);

    static PyObject* varWithPosition(const PyObject* var, const PyObject* pos);

private:
    // singleton instance
    static PyAstFreeVariableAnalyses& _getInstance() {
        static PyAstFreeVariableAnalyses instance;
        return instance;
        }

    // implement, but keep private for singleton pattern
    PyAstFreeVariableAnalyses();
    // don't implement these next two methods for the singleton pattern
    PyAstFreeVariableAnalyses(const PyAstFreeVariableAnalyses&);
    void operator=(const PyAstFreeVariableAnalyses&);

    void _initPyAstFreeVariableAnalysesModule();
    void _initGetFreeVariableMemberAccessChainsFun();
    void _initVarWithPosition();

    PyObject* mPyAstFreeVariableAnalysesModule;
    PyObject* mGetFreeVariableMemberAccessChainsFun;
    PyObject* mVarWithPosition;
    };
