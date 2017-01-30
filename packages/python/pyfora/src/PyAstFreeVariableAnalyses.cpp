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
#include "PyAstFreeVariableAnalyses.hpp"

#include "PyObjectUtils.hpp"

#include <exception>
#include <stdexcept>


PyAstFreeVariableAnalyses::PyAstFreeVariableAnalyses()
    {
    _initPyAstFreeVariableAnalysesModule();
    _initGetFreeVariableMemberAccessChainsFun();
    _initVarWithPosition();
    }


void PyAstFreeVariableAnalyses::_initVarWithPosition()
    {
    mVarWithPosition = PyObjectPtr::unincremented(
            PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule.get(),
                                   "VarWithPosition")
        );
    if (mVarWithPosition == nullptr) {
        throw std::runtime_error("error getting VarWithPosition attr "
                               "on PyAstFreeVariableAnalyses module");
        }
    }


void PyAstFreeVariableAnalyses::_initPyAstFreeVariableAnalysesModule()
    {
    mPyAstFreeVariableAnalysesModule = 
        PyObjectPtr::unincremented(
            PyImport_ImportModule("pyfora.pyAst.PyAstFreeVariableAnalyses"));
    if (mPyAstFreeVariableAnalysesModule == nullptr) {
        throw std::runtime_error(
            "py err in _initPyAstFreeVariableAnalysesModule: " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstFreeVariableAnalyses::_initGetFreeVariableMemberAccessChainsFun()
    {
    mGetFreeVariableMemberAccessChainsFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule.get(),
                               "getFreeVariableMemberAccessChains")
        );

    if (mGetFreeVariableMemberAccessChainsFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstFreeVariableAnalyses::_initGetFreeVariableMemberAccessChainsFun(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


PyObject* PyAstFreeVariableAnalyses::getFreeMemberAccessChainsWithPositions(
        const PyObject* pyAst,
        bool isClassContext,
        bool getPositions,
        const PyObject* exclude_predicate) const
    {
    PyObjectPtr pyIsClassContext = PyObjectPtr::unincremented(
        PyBool_FromLong(isClassContext));
    if (pyIsClassContext == nullptr) {
        return nullptr;
        }

    PyObjectPtr pyGetPositions = PyObjectPtr::unincremented(
        PyBool_FromLong(getPositions));
    if (pyGetPositions == nullptr) {
        return nullptr;
        }

    PyObjectPtr kwds = PyObjectPtr::unincremented(
        Py_BuildValue("{s:O, s:O, s:O, s:O}",
            "pyAstNode",
            pyAst,
            "isClassContext",
            pyIsClassContext.get(),
            "getPositions",
            pyGetPositions.get(),
            "exclude_predicate",
            exclude_predicate
            ));
    if (kwds == nullptr) {
        return nullptr;
        }

    PyObjectPtr argsTuple = PyObjectPtr::unincremented(Py_BuildValue("()"));
    if (argsTuple == nullptr) {
        return nullptr;
        }

    return PyObject_Call(
        mGetFreeVariableMemberAccessChainsFun.get(),
        argsTuple.get(),
        kwds.get());
    }


PyObject* PyAstFreeVariableAnalyses::collectBoundValuesInScope(
        const PyObject* pyAst,
        bool getPositions
        ) const
    {
    PyObjectPtr collectBoundValuesInScopeFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstFreeVariableAnalysesModule.get(),
            "collectBoundValuesInScope"
            ));
    if (collectBoundValuesInScopeFun == nullptr) {
        return nullptr;
        }

    PyObject* pyBool = getPositions ? Py_True : Py_False;

    return PyObject_CallFunctionObjArgs(
        collectBoundValuesInScopeFun.get(),
        pyAst,
        pyBool,
        nullptr
        );    
    }


PyObject* PyAstFreeVariableAnalyses::varWithPosition(const PyObject* var,
                                                     const PyObject* pos) const
    {
    PyObjectPtr varTup = PyObjectPtr::unincremented(Py_BuildValue("(O)", var));
    if (varTup == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        mVarWithPosition.get(),
        varTup.get(),
        pos,
        nullptr);
    }
