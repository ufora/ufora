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

#include "Exceptions.hpp"
#include "PyObjectUtils.hpp"
#include "exceptions/PyforaErrors.hpp"
#include "core/variant.hpp"

#include <stdexcept>


PyAstUtil::PyAstUtil() 
    : mPyforaInspectModule(PyforaInspect())
    {
    mPyAstUtilModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.pyAst.PyAstUtil"));
    if (mPyAstUtilModule == nullptr) {
        throw std::runtime_error(
            "py err in PyAstUtil::_initPyAstUtilModule(): " +
            PyObjectUtils::format_exc()
            );
        }
    }


std::shared_ptr<PyforaError> PyAstUtil::translateErrorToCpp() const
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

        return std::shared_ptr<PyforaError>(
            new PyforaInspectError(message)
            );
        }
    else if (PyObject_IsInstance(v,
            mExceptionsModule.getCantGetSourceTextErrorClass())) {
        
        std::string message = PyObjectUtils::str_string(v);

        Py_DECREF(e);
        Py_DECREF(v);
        Py_DECREF(tb);

        return std::shared_ptr<PyforaError>(
            new CantGetSourceTextError(message)
            );
        }
    else {
        PyErr_Restore(e, v, tb);
        return std::shared_ptr<PyforaError>(
            new PyforaError(PyObjectUtils::exc_string())
            );
        }    
    }


variant<PyObjectPtr, std::shared_ptr<PyforaError>>
PyAstUtil::sourceFilenameAndText(const PyObject* pyObject) const
    {
    variant<PyObjectPtr, std::shared_ptr<PyforaError>> tr;

    PyObjectPtr getSourceFilenameAndTextFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstUtilModule.get(), "getSourceFilenameAndText"));
    if (getSourceFilenameAndTextFun == nullptr) {
        tr.set<std::shared_ptr<PyforaError>>(translateErrorToCpp());
        return tr;
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        getSourceFilenameAndTextFun.get(),
        pyObject,
        nullptr
        );

    if (res == nullptr) {
        tr.set<std::shared_ptr<PyforaError>>(translateErrorToCpp());
        }
    else {
        tr.set<PyObjectPtr>(PyObjectPtr::unincremented(res));
        }

    return tr;
    }


variant<long, std::shared_ptr<PyforaError>>
PyAstUtil::startingSourceLine(const PyObject* pyObject) const
    {
    variant<long, std::shared_ptr<PyforaError>> tr;

    PyObjectPtr getSourceLinesFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstUtilModule.get(), "getSourceLines"));
    if (getSourceLinesFun == nullptr) {
        throw std::runtime_error(
            "error getting sourceLines fun in PyAstUtil::startingSourceLine: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            getSourceLinesFun.get(),
            pyObject,
            nullptr
            ));
    if (res == nullptr) {
        tr.set<std::shared_ptr<PyforaError>>(
            new CantGetSourceTextError(PyObjectUtils::exc_string())
            );
        return tr;
        }

    if (not PyTuple_Check(res.get())) {
        throw std::runtime_error(
            "expected a tuple in calling getSourceLines: expected a tuple"
            );
        }
    if (PyTuple_GET_SIZE(res.get()) != 2) {
        throw std::runtime_error(
            "we expected getSourceLines to return a tuple of length two"
            );
        }

    // borrowed reference -- don't need to decref
    PyObject* startingSourceLine = PyTuple_GET_ITEM(res.get(), 1);
    if (not PyInt_Check(startingSourceLine)) {
        throw std::runtime_error(
            "expected PyforaInspect.getSourceLines to return an int");
        }

    tr.set<long>(PyInt_AS_LONG(startingSourceLine));

    return tr;
    }


PyObject* PyAstUtil::pyAstFromText(const std::string& fileText) const
    {
    PyObjectPtr pyString = PyObjectPtr::unincremented(
        PyString_FromStringAndSize(
            fileText.data(),
            fileText.size()));
    if (pyString == nullptr) {
        return nullptr;
        }

    return pyAstFromText(pyString.get());
    }


PyObject* PyAstUtil::pyAstFromText(const PyObject* pyString) const
    {
    PyObjectPtr pyAstFromTextFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstUtilModule.get(), "pyAstFromText"));
    if (pyAstFromTextFun == nullptr) {
        return nullptr;
        }    

    return PyObject_CallFunctionObjArgs(
        pyAstFromTextFun.get(),
        pyString,
        nullptr
        );
    }


PyObject*
PyAstUtil::functionDefOrLambdaAtLineNumber(const PyObject* pyObject,
                                           long sourceLine) const
    {
    PyObjectPtr pySourceLine = PyObjectPtr::unincremented(
        PyInt_FromLong(sourceLine));
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObjectPtr functionDefOrLambdaAtLineNumberFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstUtilModule.get(),
                               "functionDefOrLambdaAtLineNumber")
        );

    if (functionDefOrLambdaAtLineNumberFun == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        functionDefOrLambdaAtLineNumberFun.get(),
        pyObject,
        pySourceLine.get(),
        nullptr
        );
    }


PyObject*
PyAstUtil::classDefAtLineNumber(const PyObject* pyObject,
                                long sourceLine) const
    {
    PyObjectPtr pySourceLine = PyObjectPtr::unincremented(
        PyInt_FromLong(sourceLine));
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObjectPtr classDefAtLineNumberFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(mPyAstUtilModule.get(),
                               "classDefAtLineNumber")
        );

    if (classDefAtLineNumberFun == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        classDefAtLineNumberFun.get(),
        pyObject,
        pySourceLine.get(),
        nullptr
        );
    }


PyObject*
PyAstUtil::withBlockAtLineNumber(const PyObject* pyObject, long sourceLine) const
    {
    PyObjectPtr pySourceLine = PyObjectPtr::unincremented(
        PyInt_FromLong(sourceLine));
    if (pySourceLine == nullptr) {
        return nullptr;
        }

    PyObjectPtr withBlockAtLineNumberFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "withBlockAtLineNumber"));
    if (withBlockAtLineNumberFun == nullptr) {
        return nullptr;
        }
    
    return PyObject_CallFunctionObjArgs(
        withBlockAtLineNumberFun.get(),
        pyObject,
        pySourceLine.get(),
        nullptr);
    }


variant<PyObjectPtr, std::shared_ptr<PyforaError>>
PyAstUtil::collectDataMembersSetInInit(PyObject* pyObject) const
    {
    variant<PyObjectPtr, std::shared_ptr<PyforaError>> tr;

    PyObjectPtr collectDataMembersSetInInitFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "collectDataMembersSetInInit"));
    if (collectDataMembersSetInInitFun == nullptr) {
        throw std::runtime_error(
            "error getting py collectDataMembersSetInInitFun "
            "in PyAstUtil::collectDataMembersSetInInit"
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        collectDataMembersSetInInitFun.get(),
        pyObject,
        nullptr
        );

    if (res == nullptr) {
        tr.set<std::shared_ptr<PyforaError>>(translateErrorToCpp());
        return tr;
        }

    tr.set<PyObjectPtr>(PyObjectPtr::unincremented(res));
    return tr;
    }


bool PyAstUtil::hasReturnInOuterScope(const PyObject* pyAst) const
    {
    PyObjectPtr hasReturnInOuterScopeFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "hasReturnInOuterScope"));
    if (hasReturnInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting hasReturnInOuterScope attr on PyAstUtil module");
        }

    PyObjectPtr pyBool = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            hasReturnInOuterScopeFun.get(),
            pyAst,
            nullptr));
    if (pyBool == nullptr) {
        throw std::runtime_error("error calling hasReturnInOuterScope");
        }
    if (not PyBool_Check(pyBool.get())) {
        throw std::runtime_error("expected a bool returned from hasReturnInOuterScope");
        }

    return pyBool == Py_True;
    }


bool PyAstUtil::hasYieldInOuterScope(const PyObject* pyAst) const
    {
    PyObjectPtr hasYieldInOuterScopeFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "hasYieldInOuterScope"));
    if (hasYieldInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting hasYieldInOuterScope attr on PyAstUtil module");
        }

    PyObjectPtr pyBool = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            hasYieldInOuterScopeFun.get(),
            pyAst,
            nullptr));
    if (pyBool == nullptr) {
        throw std::runtime_error("error calling hasYieldInOuterScope");
        }
    if (not PyBool_Check(pyBool.get())) {
        throw std::runtime_error("expected a bool returned from hasYieldInOuterScope");
        }

    return pyBool == Py_True;
    }


long PyAstUtil::getYieldLocationsInOuterScope(const PyObject* pyAstNode) const
    {
    PyObjectPtr getYieldLocationsInOuterScopeFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "getYieldLocationsInOuterScope"
            ));
    if (getYieldLocationsInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting getYieldLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            getYieldLocationsInOuterScopeFun.get(),
            pyAstNode,
            nullptr
            ));

    if (res == nullptr) {
        throw std::runtime_error(
            "error calling getYieldLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyList_Check(res.get())) {
        throw std::runtime_error(
            "expected return type of getYieldLocationsInOuterScope to be a list"
            );
        }
    if (PyList_GET_SIZE(res.get()) == 0) {
        throw std::runtime_error(
            "expected getYieldLocationsInOuterScope to return a list of length"
            " at least one"
            );
        }

    // borrowed reference
    PyObject* item = PyList_GET_ITEM(res.get(), 0);

    if (not PyInt_Check(item)) {
        throw std::runtime_error(
            "expected elements in returned list from getYieldLocationsInOuterScope"
            " to all be ints"
            );            
        }
    
    return PyInt_AS_LONG(item);
    }


long PyAstUtil::getReturnLocationsInOuterScope(const PyObject* pyAstNode) const
    {
    PyObjectPtr getReturnLocationsInOuterScopeFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPyAstUtilModule.get(),
            "getReturnLocationsInOuterScope"
            ));
    if (getReturnLocationsInOuterScopeFun == nullptr) {
        throw std::runtime_error(
            "error getting getReturnLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            getReturnLocationsInOuterScopeFun.get(),
            pyAstNode,
            nullptr
            ));
    
    if (res == nullptr) {
        throw std::runtime_error(
            "error calling getReturnLocationsInOuterScopeFun: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyList_Check(res.get())) {
        throw std::runtime_error(
            "expected return type of getReturnLocationsInOuterScope to be a list"
            );
        }
    if (PyList_GET_SIZE(res.get()) == 0) {
        throw std::runtime_error(
            "expected getReturnLocationsInOuterScope to return a list of length"
            " at least one"
            );
        }

    // borrowed reference
    PyObject* item = PyList_GET_ITEM(res.get(), 0);

    if (not PyInt_Check(item)) {
        throw std::runtime_error(
            "expected elements in returned list from getReturnLocationsInOuterScope"
            " to all be ints"
            );            
        }
    
    return PyInt_AS_LONG(item);
    }
