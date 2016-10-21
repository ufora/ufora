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
    : mPyAstUtilModule(nullptr),
      mGetSourceFilenameAndTextFun(nullptr),
      mGetSourceLinesFun(nullptr),
      mPyAstFromTextFun(nullptr),
      mFunctionDefOrLambdaAtLineNumberFun(nullptr),
      mClassDefAtLineNumberFun(nullptr)
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

    if (mClassDefAtLineNumberFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initClassDefAtLineNumberFun: " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstUtil::_initFunctionDefOrLambdaAtLineNumberFun()
    {
    mFunctionDefOrLambdaAtLineNumberFun =
        PyObject_GetAttrString(mPyAstUtilModule,
                               "functionDefOrLambdaAtLineNumber");

    if (mFunctionDefOrLambdaAtLineNumberFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initFunctionDefOrLambdaAtLineNumberFun(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstUtil::_initPyAstFromTextFun()
    {
    mPyAstFromTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "pyAstFromText");
    if (mPyAstFromTextFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initPyAstFromTextFun(): " +
            PyObjectUtils::format_exc()
            );
        }    
    }


void PyAstUtil::_initGetSourceLinesFun()
    {
    mGetSourceLinesFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceLines");
    if (mGetSourceLinesFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initGetSourceLinesFun(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstUtil::_initGetSourceFilenameAndTextFun()
    {
    mGetSourceFilenameAndTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceFilenameAndText");
    if (mGetSourceFilenameAndTextFun == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initGetSourceFilenameAndTextFun(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstUtil::_initPyAstUtilModule()
    {
    mPyAstUtilModule = PyImport_ImportModule("pyfora.pyAst.PyAstUtil");
    if (mPyAstUtilModule == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initPyAstUtilModule(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


PyObject*
PyAstUtil::sourceFilenameAndText(const PyObject* pyObject)
    {
    PyObject * tr = PyObject_CallFunctionObjArgs(
        _getInstance().mGetSourceFilenameAndTextFun,
        pyObject,
        nullptr
        );

    if (tr == nullptr) {
        _translateError();
        }

    return tr;
    }


long PyAstUtil::startingSourceLine(const PyObject* pyObject)
    {
    PyObject* res = PyObject_CallFunctionObjArgs(
        _getInstance().mGetSourceLinesFun,
        pyObject,
        nullptr
        );
    if (res == nullptr) {
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
    if (not PyInt_Check(startingSourceLine)) {
        Py_DECREF(res);
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
    if (pyString == nullptr) {
        return nullptr;
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
        nullptr
        );
    }


PyObject*
PyAstUtil::functionDefOrLambdaAtLineNumber(const PyObject* pyObject,
                                           long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mFunctionDefOrLambdaAtLineNumberFun,
        pyObject,
        pySourceLine,
        nullptr
        );

    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* 
PyAstUtil::classDefAtLineNumber(const PyObject* pyObject,
                                long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mClassDefAtLineNumberFun,
        pyObject,
        pySourceLine,
        nullptr
        );

    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* PyAstUtil::withBlockAtLineNumber(const PyObject* pyObject, long sourceLine)
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* withBlockAtLineNumberFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "withBlockAtLineNumber");
    if (withBlockAtLineNumberFun == nullptr) {
        Py_DECREF(pySourceLine);
        return nullptr;
        }
    
    PyObject* tr = PyObject_CallFunctionObjArgs(
        withBlockAtLineNumberFun,
        pyObject,
        pySourceLine,
        nullptr);
    
    Py_DECREF(withBlockAtLineNumberFun);
    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject* PyAstUtil::collectDataMembersSetInInit(PyObject* pyObject)
    {
    PyObject* collectDataMembersSetInInitFun = PyObject_GetAttrString(
        _getInstance().mPyAstUtilModule,
        "collectDataMembersSetInInit");
    if (collectDataMembersSetInInitFun == nullptr) {
        return nullptr;
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        collectDataMembersSetInInitFun,
        pyObject,
        nullptr
        );

    Py_DECREF(collectDataMembersSetInInitFun);

    if (res == nullptr) {
        _translateError();
        }

    return res;
    }


void PyAstUtil::_translateError() {
    PyObject * e, * v, * tb;

    PyErr_Fetch(&e, &v, &tb);
    if (e == nullptr) {
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
    if (hasReturnInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting hasReturnInOuterScope attr on PyAstUtil module");
        }

    PyObject* pyBool = PyObject_CallFunctionObjArgs(
        hasReturnInOuterScopeFun,
        pyAst,
        nullptr);
    Py_DECREF(hasReturnInOuterScopeFun);
    if (pyBool == nullptr) {
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
    if (hasYieldInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting hasYieldInOuterScope attr on PyAstUtil module");
        }

    PyObject* pyBool = PyObject_CallFunctionObjArgs(
        hasYieldInOuterScopeFun,
        pyAst,
        nullptr);
    Py_DECREF(hasYieldInOuterScopeFun);
    if (pyBool == nullptr) {
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
    if (getYieldLocationsInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting getYieldLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getYieldLocationsInOuterScopeFun,
        pyAstNode,
        nullptr
        );
    
    Py_DECREF(getYieldLocationsInOuterScopeFun);

    if (res == nullptr) {
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
    if (getReturnLocationsInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting getReturnLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getReturnLocationsInOuterScopeFun,
        pyAstNode,
        nullptr
        );
    
    Py_DECREF(getReturnLocationsInOuterScopeFun);

    if (res == nullptr) {
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
