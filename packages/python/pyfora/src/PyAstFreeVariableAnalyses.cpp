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

#include <iostream>
#include <exception>
#include <stdexcept>


PyAstFreeVariableAnalyses::PyAstFreeVariableAnalyses()
    : mPyAstFreeVariableAnalysesModule(NULL),
      mGetFreeVariableMemberAccessChainsFun(NULL),
      mVarWithPosition(NULL)
    {
    _initPyAstFreeVariableAnalysesModule();
    _initGetFreeVariableMemberAccessChainsFun();
    _initVarWithPosition();
    }


void PyAstFreeVariableAnalyses::_initVarWithPosition()
    {
    mVarWithPosition = PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule,
                                              "VarWithPosition");
    if (mVarWithPosition == NULL) {
        throw std::runtime_error("error getting VarWithPosition attr "
                               "on PyAstFreeVariableAnalyses module");
        }
    }


void PyAstFreeVariableAnalyses::_initPyAstFreeVariableAnalysesModule()
    {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    if (pyforaModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import pyfora module");
        }

    PyObject* pyAstModule = PyObject_GetAttrString(pyforaModule,
                                                   "pyAst");
    if (pyAstModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't access member pyAst of pyfora");
        }

    mPyAstFreeVariableAnalysesModule = 
        PyObject_GetAttrString(pyAstModule,
                               "PyAstFreeVariableAnalyses");
    if (mPyAstFreeVariableAnalysesModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import PyAstFreeVariableAnalyses module");
        }
    
    Py_DECREF(pyAstModule);
    Py_DECREF(pyforaModule);
    }


void PyAstFreeVariableAnalyses::_initGetFreeVariableMemberAccessChainsFun()
    {
    mGetFreeVariableMemberAccessChainsFun =
        PyObject_GetAttrString(mPyAstFreeVariableAnalysesModule,
                               "getFreeVariableMemberAccessChains");

    if (mGetFreeVariableMemberAccessChainsFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `getFreeVariableMemberAccessChains` "
                              "member of PyAstUtilModule");
        }
    }


PyObject* PyAstFreeVariableAnalyses::getFreeMemberAccessChainsWithPositions(
        const PyObject* pyAst,
        bool isClassContext,
        bool getPositions,
        const PyObject* exclude_predicate)
    {
    PyObject* pyIsClassContext = PyBool_FromLong(isClassContext);
    if (pyIsClassContext == NULL) {
        return NULL;
        }

    PyObject* pyGetPositions = PyBool_FromLong(getPositions);
    if (pyGetPositions == NULL) {
        Py_DECREF(pyIsClassContext);
        return NULL;
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
    if (kwds == NULL) {
        Py_DECREF(pyGetPositions);
        Py_DECREF(pyIsClassContext);
        return NULL;
        }

    PyObject* argsTuple = Py_BuildValue("()");
    if (argsTuple == NULL) {
        Py_DECREF(kwds);
        Py_DECREF(pyGetPositions);
        Py_DECREF(pyIsClassContext);
        return NULL;
        }

    PyObject* res = PyObject_Call(
        _getInstance().mGetFreeVariableMemberAccessChainsFun,
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
        )
    {
    PyObject* collectBoundValuesInScopeFun = PyObject_GetAttrString(
        _getInstance().mPyAstFreeVariableAnalysesModule,
        "collectBoundValuesInScope"
        );
    if (collectBoundValuesInScopeFun == NULL) {
        return NULL;
        }

    // don't need to decref this creature since we're using it as a temporary
    PyObject* pyBool = (getPositions ? Py_True : Py_False);
    Py_INCREF(pyBool);

    PyObject* res = PyObject_CallFunctionObjArgs(
        collectBoundValuesInScopeFun,
        pyAst,
        pyBool,
        NULL
        );
    
    Py_DECREF(pyBool);
    Py_DECREF(collectBoundValuesInScopeFun);

    return res;
    }


PyObject* PyAstFreeVariableAnalyses::varWithPosition(const PyObject* var,
                                                     const PyObject* pos)
    {
    PyObject* varTup = Py_BuildValue("(O)", var);
    if (varTup == NULL) {
        return NULL;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mVarWithPosition,
        varTup,
        pos,
        NULL);

    Py_DECREF(varTup);

    return tr;
    }
