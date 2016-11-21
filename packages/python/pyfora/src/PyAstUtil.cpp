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
#include "PyforaInspectError.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


PyAstUtil::PyAstUtil(const PyAstUtil& other)
    : mPyAstUtilModule(other.mPyAstUtilModule),
      mPyforaInspectModule(other.mPyforaInspectModule)
    {
    Py_INCREF(mPyAstUtilModule);
    }    


PyAstUtil::~PyAstUtil()
    {
    Py_XDECREF(mPyAstUtilModule);
    }


PyAstUtil::PyAstUtil() 
    : mPyAstUtilModule(nullptr),
      mPyforaInspectModule(PyforaInspect())
    {
    mPyAstUtilModule = PyImport_ImportModule("pyfora.pyAst.PyAstUtil");
    if (mPyAstUtilModule == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initPyAstUtilModule(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


void PyAstUtil::_translateError() const
    {
    PyObject * e, * v, * tb;

    PyErr_Fetch(&e, &v, &tb);
    if (e == NULL) {
        throw std::runtime_error(
            "expected an exception to be set"
            );
        }

    PyErr_NormalizeException(&e, &v, &tb);

    if (PyObject_IsInstance(v,
            mPyforaInspectModule.getPyforaInspectErrorClass())) {
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


PyObject*
PyAstUtil::sourceFilenameAndText(const PyObject* pyObject) const
    {
    PyObject* getSourceFilenameAndTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceFilenameAndText");
    if (getSourceFilenameAndTextFun == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        getSourceFilenameAndTextFun,
        pyObject,
        nullptr
        );

    Py_DECREF(getSourceFilenameAndTextFun);

    if (tr == nullptr) {
        _translateError();
        }

    return tr;
    }


long PyAstUtil::startingSourceLine(const PyObject* pyObject) const
    {
    PyObject* getSourceLinesFun =
        PyObject_GetAttrString(mPyAstUtilModule, "getSourceLines");
    if (getSourceLinesFun == nullptr) {
        throw std::runtime_error(
            "error getting sourceLines fun in PyAstUtil::startingSourceLine: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getSourceLinesFun,
        pyObject,
        nullptr
        );
    Py_DECREF(getSourceLinesFun);
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


PyObject* PyAstUtil::pyAstFromText(const std::string& fileText) const
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


PyObject* PyAstUtil::pyAstFromText(const PyObject* pyString) const
    {
    PyObject* pyAstFromTextFun =
        PyObject_GetAttrString(mPyAstUtilModule, "pyAstFromText");
    if (pyAstFromTextFun == nullptr) {
        return nullptr;
        }    

    PyObject* tr = PyObject_CallFunctionObjArgs(
        pyAstFromTextFun,
        pyString,
        nullptr
        );

    Py_DECREF(pyAstFromTextFun);

    return tr;
    }


PyObject*
PyAstUtil::functionDefOrLambdaAtLineNumber(const PyObject* pyObject,
                                           long sourceLine) const
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* functionDefOrLambdaAtLineNumberFun =
        PyObject_GetAttrString(mPyAstUtilModule,
                               "functionDefOrLambdaAtLineNumber");

    if (functionDefOrLambdaAtLineNumberFun == nullptr) {
        Py_DECREF(pySourceLine);
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        functionDefOrLambdaAtLineNumberFun,
        pyObject,
        pySourceLine,
        nullptr
        );

    Py_DECREF(functionDefOrLambdaAtLineNumberFun);
    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject*
PyAstUtil::classDefAtLineNumber(const PyObject* pyObject,
                                long sourceLine) const
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* classDefAtLineNumberFun =
        PyObject_GetAttrString(mPyAstUtilModule,
                               "classDefAtLineNumber");

    if (classDefAtLineNumberFun == nullptr) {
        Py_DECREF(pySourceLine);
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        classDefAtLineNumberFun,
        pyObject,
        pySourceLine,
        nullptr
        );

    Py_DECREF(classDefAtLineNumberFun);
    Py_DECREF(pySourceLine);

    return tr;
    }


PyObject*
PyAstUtil::withBlockAtLineNumber(const PyObject* pyObject, long sourceLine) const
    {
    PyObject* pySourceLine = PyInt_FromLong(sourceLine);
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObject* withBlockAtLineNumberFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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


PyObject* PyAstUtil::collectDataMembersSetInInit(PyObject* pyObject) const
    {
    PyObject* collectDataMembersSetInInitFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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


bool PyAstUtil::hasReturnInOuterScope(const PyObject* pyAst) const
    {
    PyObject* hasReturnInOuterScopeFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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


bool PyAstUtil::hasYieldInOuterScope(const PyObject* pyAst) const
    {
    PyObject* hasYieldInOuterScopeFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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


long PyAstUtil::getYieldLocationsInOuterScope(const PyObject* pyAstNode) const
    {
    PyObject* getYieldLocationsInOuterScopeFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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


long PyAstUtil::getReturnLocationsInOuterScope(const PyObject* pyAstNode) const
    {
    PyObject* getReturnLocationsInOuterScopeFun = PyObject_GetAttrString(
        mPyAstUtilModule,
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
