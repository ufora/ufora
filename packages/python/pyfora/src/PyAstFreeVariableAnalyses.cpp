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


PyAstFreeVariableAnalyses::~PyAstFreeVariableAnalyses()
    {
    Py_XDECREF(mVarWithPosition);
    Py_XDECREF(mGetFreeVariableMemberAccessChainsFun);
    Py_XDECREF(mPyAstFreeVariableAnalysesModule);
    }


PyAstFreeVariableAnalyses::PyAstFreeVariableAnalyses(const PyAstFreeVariableAnalyses& other)
    : mPyAstFreeVariableAnalysesModule(other.mPyAstFreeVariableAnalysesModule),
      mGetFreeVariableMemberAccessChainsFun(other.mGetFreeVariableMemberAccessChainsFun),
      mVarWithPosition(other.mVarWithPosition)
    {
    Py_INCREF(mPyAstFreeVariableAnalysesModule);
    Py_INCREF(mGetFreeVariableMemberAccessChainsFun);
    Py_INCREF(mVarWithPosition);
    }


PyAstFreeVariableAnalyses::PyAstFreeVariableAnalyses()
    : mPyAstFreeVariableAnalysesModule(nullptr),
      mGetFreeVariableMemberAccessChainsFun(nullptr),
      mVarWithPosition(nullptr)
    {
    _initPyAstFreeVariableAnalysesModule();
    _initGetFreeVariableMemberAccessChainsFun();
    _initVarWithPosition();
    }


void PyAstFreeVariableAnalyses::_initVarWithPosition()
    {
    mVarWithPosition = PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule,
                                              "VarWithPosition");
    if (mVarWithPosition == nullptr) {
        throw std::runtime_error("error getting VarWithPosition attr "
                               "on PyAstFreeVariableAnalyses module");
        }
    }


void PyAstFreeVariableAnalyses::_initPyAstFreeVariableAnalysesModule()
    {
    mPyAstFreeVariableAnalysesModule = 
        PyImport_ImportModule("pyfora.pyAst.PyAstFreeVariableAnalyses");
    if (mPyAstFreeVariableAnalysesModule == nullptr) {
        throw std::runtime_error(
            "py err in _initPyAstFreeVariableAnalysesModule: " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstFreeVariableAnalyses::_initGetFreeVariableMemberAccessChainsFun()
    {
    mGetFreeVariableMemberAccessChainsFun =
        PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule,
                               "getFreeVariableMemberAccessChains");

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
    PyObject* pyIsClassContext = PyBool_FromLong(isClassContext);
    if (pyIsClassContext == nullptr) {
        return nullptr;
        }

    PyObject* pyGetPositions = PyBool_FromLong(getPositions);
    if (pyGetPositions == nullptr) {
        Py_DECREF(pyIsClassContext);
        return nullptr;
        }

    PyObject* kwds = Py_BuildValue("{s:O, s:O, s:O, s:O}",
        "pyAstNode",
        pyAst,
        "isClassContext",
        pyIsClassContext,
        "getPositions",
        pyGetPositions,
        "exclude_predicate",
        exclude_predicate
        );
    if (kwds == nullptr) {
        Py_DECREF(pyGetPositions);
        Py_DECREF(pyIsClassContext);
        return nullptr;
        }

    PyObject* argsTuple = Py_BuildValue("()");
    if (argsTuple == nullptr) {
        Py_DECREF(kwds);
        Py_DECREF(pyGetPositions);
        Py_DECREF(pyIsClassContext);
        return nullptr;
        }

    PyObject* res = PyObject_Call(
        mGetFreeVariableMemberAccessChainsFun,
        argsTuple,
        kwds);

    Py_DECREF(argsTuple);
    Py_DECREF(kwds);
    Py_DECREF(pyGetPositions);
    Py_DECREF(pyIsClassContext);
    
    return res;
    }


PyObject* PyAstFreeVariableAnalyses::collectBoundValuesInScope(
        const PyObject* pyAst,
        bool getPositions
        ) const
    {
    PyObject* collectBoundValuesInScopeFun = PyObject_GetAttrString(
        mPyAstFreeVariableAnalysesModule,
        "collectBoundValuesInScope"
        );
    if (collectBoundValuesInScopeFun == nullptr) {
        return nullptr;
        }

    // don't need to decref this creature since we're using it as a temporary
    PyObject* pyBool = (getPositions ? Py_True : Py_False);
    Py_INCREF(pyBool);

    PyObject* res = PyObject_CallFunctionObjArgs(
        collectBoundValuesInScopeFun,
        pyAst,
        pyBool,
        nullptr
        );
    
    Py_DECREF(pyBool);
    Py_DECREF(collectBoundValuesInScopeFun);

    return res;
    }


PyObject* PyAstFreeVariableAnalyses::varWithPosition(const PyObject* var,
                                                     const PyObject* pos) const
    {
    PyObject* varTup = Py_BuildValue("(O)", var);
    if (varTup == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        mVarWithPosition,
        varTup,
        pos,
        nullptr);

    Py_DECREF(varTup);

    return tr;
    }
