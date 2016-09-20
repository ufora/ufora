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
#include "PyAstUtil.hpp"

#include "CantGetSourceTextError.hpp"
#include "PyforaInspect.hpp"
#include "PyforaInspectError.hpp"
#include "PyObjectUtils.hpp"

#include <iostream>
#include <stdexcept>


PyAstUtil::PyAstUtil()
    : mPyAstUtilModule(NULL),
      mGetSourceFilenameAndTextFun(NULL),
      mGetSourceLinesFun(NULL),
      mPyAstFromTextFun(NULL),
      mFunctionDefOrLambdaAtLineNumberFun(NULL),
      mClassDefAtLineNumberFun(NULL)
    {
    _initPyAstUtilModule();
    _initGetSourceFilenameAndTextFun();
    _initGetSourceLinesFun();
    _initPyAstFromTextFun();
    _initFunctionDefOrLambdaAtLineNumberFun();
    _initClassDefAtLineNumberFun();
    }


void PyAstUtil::_initClassDefAtLineNumberFun()
    {
    mClassDefAtLineNumberFun =
        PyObject_GetAttrString(mPyAstUtilModule,
                               "classDefAtLineNumber");

    if (mClassDefAtLineNumberFun == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "couldn't get `classDefAtLineNumber` member"
            " of PyAstUtilModule");
        }
    }


void PyAstUtil::_initFunctionDefOrLambdaAtLineNumberFun()
    {
    mFunctionDefOrLambdaAtLineNumberFun =
        PyObject_GetAttrString(mPyAstUtilModule,
                               "functionDefOrLambdaAtLineNumber");

    if (mFunctionDefOrLambdaAtLineNumberFun == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "couldn't get `functionDefOrLambdaAtLineNumber` member"
            " of PyAstUtilModule");
        }
    }


void PyAstUtil::_initPyAstFromTextFun()
    {
    mPyAstFromTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "pyAstFromText");
    if (mPyAstFromTextFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `pyAstFromText` member"
                               " of PyAstUtilModule");
        }    
    }


void PyAstUtil::_initGetSourceLinesFun()
    {
    mGetSourceLinesFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceLines");
    if (mGetSourceLinesFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `getSourceLines` member"
                               " of PyAstUtilModule");
        }
    }


void PyAstUtil::_initGetSourceFilenameAndTextFun()
    {
    mGetSourceFilenameAndTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceFilenameAndText");
    if (mGetSourceFilenameAndTextFun == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't get `getSourceFilenameAndText` member"
                               " of PyAstUtilModule");
        }
    }


void PyAstUtil::_initPyAstUtilModule()
    {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    if (pyforaModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import pyfora module");
        }

    PyObject* pyAstModule = PyObject_GetAttrString(pyforaModule, "pyAst");
    if (pyAstModule == NULL) {
        PyErr_Print();
        Py_DECREF(pyforaModule);
        throw std::runtime_error("couldn't find pyAst member on pyfora");
        }

    mPyAstUtilModule = PyObject_GetAttrString(pyAstModule, "PyAstUtil");
    Py_DECREF(pyAstModule);
    Py_DECREF(pyforaModule);
    if (mPyAstUtilModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import PyAstUtil module");
        }
    }


PyObject*
PyAstUtil::sourceFilenameAndText(const PyObject* pyObject)
    {
    PyObject * tr = PyObject_CallFunctionObjArgs(
        _getInstance().mGetSourceFilenameAndTextFun,
        pyObject,
        NULL
        );

    if (tr == NULL) {
        _translateError();
        }

    return tr;
    }


long PyAstUtil::startingSourceLine(const PyObject* pyObject)
    {
    PyObject* res = PyObject_CallFunctionObjArgs(
        _getInstance().mGetSourceLinesFun,
        pyObject,
        NULL
        );
    if (res == NULL) {
        throw CantGetSourceTextError(PyObjectUtils::exc_string());
        }

    if (not PyTuple_Check(res)) {
        throw std::runtime_error(
            "expected a tuple in calling getSourceLines: expected a tuple"
            );
        }
    if (PyTuple_GET_SIZE(res) != 2) {
        throw std::runtime_error(
            "we expected getSourceLines to return a tuple of length two"
            );
        }

    // borrowed reference -- don't need to decref
    PyObject* startingSourceLine = PyTuple_GET_ITEM(res, 1);
    if (startingSourceLine == NULL) {
        PyErr_Print();
        throw std::runtime_error("hit an error calling PyforaInspect.getSourceLines");
        }

    if (not PyInt_Check(startingSourceLine)) {
        throw std::runtime_error(
            "expected PyforaInspect.getSourceLines to return an int");
        }

    long tr = PyInt_AS_LONG(startingSourceLine);

    Py_DECREF(res);

    return tr;
    }


PyObject* PyAstUtil::pyAstFromText(const std::string& fileText)
    {
    PyObject* pyString = PyString_FromStringAndSize(fileText.data(),
                                                    fileText.size());
    if (pyString == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't create a PyString out of a C++ string");
        }

    PyObject* res = pyAstFromText(pyString);

    Py_DECREF(pyString);

    return res;
    }


PyObject* PyAstUtil::pyAstFromText(const PyObject* pyString)
    {
    return PyObject_CallFunctionObjArgs(
        _getInstance().mPyAstFromTextFun,
        pyString,
        NULL
        );
    }


PyObject*
PyAstUtil::functionDefOrLambdaAtLineNumber(const PyObject* pyObject,
                                           long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == NULL) {
        return NULL;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mFunctionDefOrLambdaAtLineNumberFun,
        pyObject,
        pySourceLine,
        NULL
        );

    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* 
PyAstUtil::classDefAtLineNumber(const PyObject* pyObject,
                                long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == NULL) {
        return NULL;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mClassDefAtLineNumberFun,
        pyObject,
        pySourceLine,
        NULL
        );

    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* PyAstUtil::withBlockAtLineNumber(const PyObject* pyObject, long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == NULL) {
        return NULL;
        }

    PyObject* withBlockAtLineNumberFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "withBlockAtLineNumber");
    if (withBlockAtLineNumberFun == NULL) {
        Py_DECREF(pySourceLine);
        return NULL;
        }
    
    PyObject* tr = PyObject_CallFunctionObjArgs(
        withBlockAtLineNumberFun,
        pyObject,
        pySourceLine,
        NULL);
    
    Py_DECREF(withBlockAtLineNumberFun);
    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* PyAstUtil::collectDataMembersSetInInit(PyObject* pyObject)
    {
    PyObject* collectDataMembersSetInInitFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "collectDataMembersSetInInit");
    if (collectDataMembersSetInInitFun == NULL) {
        return NULL;
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        collectDataMembersSetInInitFun,
        pyObject,
        NULL
        );

    Py_DECREF(collectDataMembersSetInInitFun);

    if (res == NULL) {
        _translateError();
        }

    return res;
    }


void PyAstUtil::_translateError() {
    PyObject * e, * v, * tb;

    PyErr_Fetch(&e, &v, &tb);
    if (e == NULL) {
        throw std::runtime_error(
            "expected an exception to be set"
            );
        }

    PyErr_NormalizeException(&e, &v, &tb);

    if (PyObject_IsInstance(v,
            PyforaInspect::getPyforaInspectErrorClass())) {
        std::string message = PyObjectUtils::str_string(v);

        Py_DECREF(e);
        Py_DECREF(v);
        Py_DECREF(tb);

        throw PyforaInspectError(message);
        }
    else {
        PyErr_Restore(e, v, tb);
        throw std::runtime_error(
            PyObjectUtils::exc_string()
            );
        }
    }


bool PyAstUtil::hasReturnInOuterScope(const PyObject* pyAst)
    {
    PyObject* hasReturnInOuterScopeFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "hasReturnInOuterScope");
    if (hasReturnInOuterScopeFun == NULL) {
        throw std::runtime_error(
            "error getting hasReturnInOuterScope attr on PyAstUtil module");
        }

    PyObject* pyBool = PyObject_CallFunctionObjArgs(
        hasReturnInOuterScopeFun,
        pyAst,
        NULL);
    Py_DECREF(hasReturnInOuterScopeFun);
    if (pyBool == NULL) {
        throw std::runtime_error("error calling hasReturnInOuterScope");
        }
    if (not PyBool_Check(pyBool)) {
        Py_DECREF(pyBool);
        throw std::runtime_error("expected a bool returned from hasReturnInOuterScope");
        }

    bool tr = (pyBool == Py_True);

    Py_DECREF(pyBool);

    return tr;
    }


bool PyAstUtil::hasYieldInOuterScope(const PyObject* pyAst)
    {
    PyObject* hasYieldInOuterScopeFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "hasYieldInOuterScope");
    if (hasYieldInOuterScopeFun == NULL) {
        throw std::runtime_error(
            "error getting hasYieldInOuterScope attr on PyAstUtil module");
        }

    PyObject* pyBool = PyObject_CallFunctionObjArgs(
        hasYieldInOuterScopeFun,
        pyAst,
        NULL);
    Py_DECREF(hasYieldInOuterScopeFun);
    if (pyBool == NULL) {
        throw std::runtime_error("error calling hasYieldInOuterScope");
        }
    if (not PyBool_Check(pyBool)) {
        Py_DECREF(pyBool);
        throw std::runtime_error("expected a bool returned from hasYieldInOuterScope");
        }

    bool tr = (pyBool == Py_True);

    Py_DECREF(pyBool);

    return tr;    
    }


long PyAstUtil::getYieldLocationsInOuterScope(const PyObject* pyAstNode)
    {
    PyObject* getYieldLocationsInOuterScopeFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "getYieldLocationsInOuterScope"
        );
    if (getYieldLocationsInOuterScopeFun == NULL) {
        throw std::runtime_error(
            "error getting getYieldLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getYieldLocationsInOuterScopeFun,
        pyAstNode,
        NULL
        );
    
    Py_DECREF(getYieldLocationsInOuterScopeFun);

    if (res == NULL) {
        throw std::runtime_error(
            "error calling getYieldLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyList_Check(res)) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected return type of getYieldLocationsInOuterScope to be a list"
            );
        }
    if (PyList_GET_SIZE(res) == 0) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected getYieldLocationsInOuterScope to return a list of length"
            " at least one"
            );
        }

    PyObject* item = PyList_GET_ITEM(res, 0);

    if (not PyInt_Check(item)) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected elements in returned list from getYieldLocationsInOuterScope"
            " to all be ints"
            );            
        }
    
    long tr = PyInt_AS_LONG(item);

    // don't need to decref item -- it's a borrowed reference
    Py_DECREF(res);

    return tr;
    }


long PyAstUtil::getReturnLocationsInOuterScope(const PyObject* pyAstNode)
    {
    PyObject* getReturnLocationsInOuterScopeFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "getReturnLocationsInOuterScope"
        );
    if (getReturnLocationsInOuterScopeFun == NULL) {
        throw std::runtime_error(
            "error getting getReturnLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getReturnLocationsInOuterScopeFun,
        pyAstNode,
        NULL
        );
    
    Py_DECREF(getReturnLocationsInOuterScopeFun);

    if (res == NULL) {
        throw std::runtime_error(
            "error calling getReturnLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyList_Check(res)) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected return type of getReturnLocationsInOuterScope to be a list"
            );
        }
    if (PyList_GET_SIZE(res) == 0) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected getReturnLocationsInOuterScope to return a list of length"
            " at least one"
            );
        }

    PyObject* item = PyList_GET_ITEM(res, 0);

    if (not PyInt_Check(item)) {
        Py_DECREF(res);
        throw std::runtime_error(
            "expected elements in returned list from getReturnLocationsInOuterScope"
            " to all be ints"
            );            
        }
    
    long tr = PyInt_AS_LONG(item);

    // don't need to decref item -- it's a borrowed reference
    Py_DECREF(res);

    return tr;
    }
