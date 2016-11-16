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
#include "PyObjectWalker.hpp"

#include "Ast.hpp"
#include "BadWithBlockError.hpp"
#include "CantGetSourceTextError.hpp"
#include "ClassOrFunctionInfo.hpp"
#include "FileDescription.hpp"
#include "FreeVariableResolver.hpp"
#include "PyAstUtil.hpp"
#include "PyAstFreeVariableAnalyses.hpp"
#include "PyforaInspect.hpp"
#include "PyforaInspectError.hpp"
#include "PyObjectUtils.hpp"
#include "PythonToForaConversionError.hpp"
#include "UnresolvedFreeVariableExceptions.hpp"
#include "UnresolvedFreeVariableExceptionWithTrace.hpp"

#include <iostream>
#include <stdexcept>
#include <vector>


PyObjectWalker::PyObjectWalker(
        PyObject* purePythonClassMapping,
        BinaryObjectRegistry& objectRegistry,
        PyObject* excludePredicateFun,
        PyObject* excludeList,
        PyObject* terminalValueFilter,
        PyObject* traceback_type,
        PyObject* pythonTracebackToJsonFun) :
            mPurePythonClassMapping(purePythonClassMapping),
            mPyforaModule(NULL),
            mRemotePythonObjectClass(NULL),
            mPackedHomogenousDataClass(NULL),
            mFutureClass(NULL),
            mExcludePredicateFun(excludePredicateFun),
            mExcludeList(excludeList),
            mTerminalValueFilter(terminalValueFilter),
            mWithBlockClass(NULL),
            mGetPathToObjectFun(NULL),
            mUnconvertibleClass(NULL),
            mPyforaConnectHack(NULL),
            mTracebackType(traceback_type),
            mPythonTracebackToJsonFun(pythonTracebackToJsonFun),
            mObjectRegistry(objectRegistry),
            mFreeVariableResolver(excludeList, terminalValueFilter)
    {
    Py_INCREF(mPurePythonClassMapping);
    _initPyforaModule();
    _initPythonSingletonToName();
    _initRemotePythonObjectClass();
    _initPackedHomogenousDataClass();
    _initFutureClass();
    _initWithBlockClass();
    _initGetPathToObjectFun();
    _initUnconvertibleClass();
    _initPyforaConnectHack();
    }


void PyObjectWalker::_initPyforaModule()
    {
    mPyforaModule = PyImport_ImportModule("pyfora");

    if (mPyforaModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import pyfora module");
        }
    }


void PyObjectWalker::_initWithBlockClass()
    {
    PyObject* withBlockModule =
        PyObject_GetAttrString(mPyforaModule, "PyforaWithBlock");
    if (withBlockModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("error getting PyforaWithBlock module");
        }

    mWithBlockClass = PyObject_GetAttrString(withBlockModule, "PyforaWithBlock");
    Py_DECREF(withBlockModule);
    if (mWithBlockClass == NULL) {
        PyErr_Print();
        throw std::runtime_error("error getting PyforaWithBlock class from "
                               "PyforaWithBlock module");
        }
    }


void PyObjectWalker::_initFutureClass()
    {
    PyObject* futureModule = PyObject_GetAttrString(mPyforaModule,
                                                    "Future");

    if (futureModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import Future module");
        }

    mFutureClass = PyObject_GetAttrString(futureModule,
                                          "Future");
    Py_DECREF(futureModule);
    if (mFutureClass == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't find Future.Future");
        }
    }


void PyObjectWalker::_initPackedHomogenousDataClass()
    {
    PyObject* typeDescriptionModule = PyObject_GetAttrString(mPyforaModule,
                                                             "TypeDescription");

    if (typeDescriptionModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import TypeDescription module");
        }

    mPackedHomogenousDataClass = PyObject_GetAttrString(typeDescriptionModule,
                                                        "PackedHomogenousData");
    Py_DECREF(typeDescriptionModule);
    if (mPackedHomogenousDataClass == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't find TypeDescription.PackedHomogenousData");
        }
    }


void PyObjectWalker::_initRemotePythonObjectClass()
    {
    PyObject* remotePythonObjectModule = PyObject_GetAttrString(mPyforaModule,
                                                                "RemotePythonObject");

    if (remotePythonObjectModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import RemotePythonObjectModule");
        }

    mRemotePythonObjectClass = PyObject_GetAttrString(remotePythonObjectModule,
                                                      "RemotePythonObject");
    Py_DECREF(remotePythonObjectModule);
    if (mRemotePythonObjectClass == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't find RemotePythonObject.RemotePythonObject");
        }
    }


void PyObjectWalker::_initPythonSingletonToName()
    {
    PyObject* namedSingletonsModule = PyObject_GetAttrString(mPyforaModule,
                                                             "NamedSingletons");
    
    if (namedSingletonsModule == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't import NamedSingleTons module");
        }

    PyObject* pythonSingletonToName = PyObject_GetAttrString(namedSingletonsModule,
                                                             "pythonSingletonToName");
    Py_DECREF(namedSingletonsModule);
    if (pythonSingletonToName == NULL) {
        PyErr_Print();
        throw std::runtime_error("expected to find member pythonSingletonToName"
                               " in NamedSingletons");
        }
    if (not PyDict_Check(pythonSingletonToName)) {
        throw std::runtime_error("expected pythonSingletonToName to be a dict");
        }

    PyObject * key, * value;
    Py_ssize_t pos = 0;
    char* string = NULL;
    Py_ssize_t length = 0;

    while (PyDict_Next(pythonSingletonToName, &pos, &key, &value)) {
        if (PyString_AsStringAndSize(value, &string, &length) == -1) {
            std::runtime_error("expected values in pythonSingletonToName to be strings");
            }

        Py_INCREF(key);
        mPythonSingletonToName[key] = std::string(string, length);
        }

    Py_DECREF(pythonSingletonToName);
    }


void PyObjectWalker::_initGetPathToObjectFun()
    {
    PyObject* moduleLevelObjectIndexModule = PyObject_GetAttrString(
        mPyforaModule,
        "ModuleLevelObjectIndex"
        );
    if (moduleLevelObjectIndexModule == NULL) {
        throw std::runtime_error(
            "py error getting moduleLevelObjectIndexModule in "
            "PyObjectWalker::_initGetPathToObjectFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* moduleLevelObjectIndexClass = PyObject_GetAttrString(
        moduleLevelObjectIndexModule,
        "ModuleLevelObjectIndex"
        );
    if (moduleLevelObjectIndexClass == NULL) {
        Py_DECREF(moduleLevelObjectIndexModule);
        throw std::runtime_error(
            "py error getting moduleLevelObjectIndexClass in "
            "PyObjectWalker::_initGetPathToObjectFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* singletonFunc = PyObject_GetAttrString(
        moduleLevelObjectIndexClass,
        "singleton"
        );
    if (singletonFunc == NULL) {
        Py_DECREF(moduleLevelObjectIndexClass);
        Py_DECREF(moduleLevelObjectIndexModule);
        throw std::runtime_error(
            "py error getting singletonFunc in "
            "PyObjectWalker::_initGetPathToObjectFun: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* singleton = PyObject_CallFunctionObjArgs(
        singletonFunc,
        NULL
        );
    if (singleton == NULL) {
        Py_DECREF(singletonFunc);
        Py_DECREF(moduleLevelObjectIndexClass);
        Py_DECREF(moduleLevelObjectIndexModule);
        throw std::runtime_error(
            "py error getting singleton in "
            "PyObjectWalker::_initGetPathToObjectFun: " +
            PyObjectUtils::format_exc()
            );
        }

    mGetPathToObjectFun = PyObject_GetAttrString(
        singleton,
        "getPathToObject"
        );

    Py_DECREF(singleton);
    Py_DECREF(singletonFunc);
    Py_DECREF(moduleLevelObjectIndexClass);
    Py_DECREF(moduleLevelObjectIndexModule);

    if (mGetPathToObjectFun == NULL) {
        throw std::runtime_error(
            "py error getting getPathToObject in "
            "PyObjectWalker::_initGetPathToObjectFun: " +
            PyObjectUtils::exc_string());
        }
    }


void PyObjectWalker::_initUnconvertibleClass() {
    PyObject* unconvertibleModule = PyObject_GetAttrString(
        mPyforaModule,
        "Unconvertible"
        );
    if (unconvertibleModule == NULL) {
        throw std::runtime_error(
            "py error getting unconvertibleModule in "
            "PyObjectWalker::_initUnconvertibleClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mUnconvertibleClass = PyObject_GetAttrString(
        unconvertibleModule,
        "Unconvertible"
        );

    Py_DECREF(unconvertibleModule);

    if (mUnconvertibleClass == NULL) {
        throw std::runtime_error(
            "py error getting unconvertibleModule in "
            "PyObjectWalker::_initUnconvertibleClass " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPyforaConnectHack() {
    mPyforaConnectHack = PyObject_GetAttrString(
        mPyforaModule,
        "connect"
        );
    if (mPyforaConnectHack == NULL) {
        throw std::runtime_error(
            "py error getting pyfora.connect in "
            "PyObjectWalker::_initPyforaConnectHack: " +
            PyObjectUtils::exc_string()
            );
        }
    }


PyObjectWalker::~PyObjectWalker()
    {
    for (std::map<long, PyObject*>::const_iterator it =
            mConvertedObjectCache.begin();
        it != mConvertedObjectCache.end();
        ++it) {
        Py_DECREF(it->second);
        }

    for (std::map<PyObject*, int64_t>::const_iterator it =
             mPyObjectToObjectId.begin();
         it != mPyObjectToObjectId.end();
         ++it) {
        Py_DECREF(it->first);
        }

    for (std::map<PyObject*, std::string>::const_iterator it =
             mPythonSingletonToName.begin();
         it != mPythonSingletonToName.end();
         ++it) {
        Py_DECREF(it->first);
        }

    Py_XDECREF(mPythonTracebackToJsonFun);
    Py_XDECREF(mTracebackType);
    Py_XDECREF(mPyforaConnectHack);
    Py_XDECREF(mUnconvertibleClass);
    Py_XDECREF(mGetPathToObjectFun);
    Py_XDECREF(mWithBlockClass);
    Py_XDECREF(mTerminalValueFilter);
    Py_XDECREF(mExcludeList);
    Py_XDECREF(mExcludePredicateFun);
    Py_XDECREF(mFutureClass);
    Py_XDECREF(mPackedHomogenousDataClass);
    Py_XDECREF(mRemotePythonObjectClass);
    Py_XDECREF(mPyforaModule);
    Py_XDECREF(mPurePythonClassMapping);
    }


int64_t PyObjectWalker::_allocateId(PyObject* pyObject) {
    int64_t objectId = mObjectRegistry.allocateObject();

    Py_INCREF(pyObject);
    mPyObjectToObjectId[pyObject] = objectId;

    return objectId;
    }


int64_t PyObjectWalker::walkPyObject(PyObject* pyObject) 
    {
        {
        std::map<PyObject*, int64_t>::const_iterator it =
            mPyObjectToObjectId.find(pyObject);

        if (it != mPyObjectToObjectId.end()) {
            return it->second;
            }
        }
    
        {
        std::map<long, PyObject*>::const_iterator it =
            mConvertedObjectCache.find(
                PyObjectUtils::builtin_id(pyObject)
                );

        if (it != mConvertedObjectCache.end()) {
            pyObject = it->second;
            }
        }

    bool wasReplaced = false;
    if (_canMap(pyObject)) {
        pyObject = _pureInstanceReplacement(pyObject);

        wasReplaced = true;
        }

    int64_t objectId = _allocateId(pyObject);

    if (pyObject == mPyforaConnectHack) {
        _registerUnconvertible(objectId, Py_None);
        return objectId;
        }
    
    try {
        _walkPyObject(pyObject, objectId);
        }
    catch (const CantGetSourceTextError& e) {
        _registerUnconvertible(objectId, pyObject);
        }
    catch (const PyforaInspectError& e) {
        _registerUnconvertible(objectId, pyObject);
        }

    if (wasReplaced) {
        Py_DECREF(pyObject);
        }

    return objectId;
    }


int64_t PyObjectWalker::walkFileDescription(const FileDescription& fileDescription)
    {
    std::map<std::string, int64_t>::const_iterator it =
        mConvertedFiles.find(fileDescription.filename);

    if (it != mConvertedFiles.end()) {
        return it->second;
        }

    int64_t objectId = mObjectRegistry.allocateObject();
    
    mObjectRegistry.defineFile(objectId,
                               fileDescription.filetext,
                               fileDescription.filename
                               );

    mConvertedFiles[fileDescription.filename] = objectId;

    return objectId;
    }


bool PyObjectWalker::_canMap(PyObject* pyObject) const
    {
    PyObject* pyString = PyString_FromString("canMap");
    if (pyString == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't make a PyString from a C++ string");
        }

    PyObject* res = PyObject_CallMethodObjArgs(
        mPurePythonClassMapping,
        pyString,
        pyObject,
        NULL
        );

    Py_DECREF(pyString);

    if (res == NULL) {
        throw std::runtime_error(
            "an error occurred trying to call purePythonClassMapping.canMap: " +
            PyObjectUtils::exc_string()
            );
        }

    bool tr = false;
    if (PyObject_IsTrue(res))
        {
        tr = true;
        }

    Py_DECREF(res);

    return tr;
    }


PyObject* PyObjectWalker::_pureInstanceReplacement(PyObject* pyObject)
    {
    PyObject* pyString = PyString_FromString("mappableInstanceToPure");
    if (pyString == NULL) {
        PyErr_Print();
        throw std::runtime_error("couldn't make a PyString from a C++ string");
        }

    PyObject* pureInstance = PyObject_CallMethodObjArgs(
        mPurePythonClassMapping,
        pyString,
        pyObject,
        NULL
        );

    Py_DECREF(pyString);

    if (pureInstance == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "an error occurred trying to call "
            "purePythonClassMapping.mappableInstanceToPure"
            );
        }

    mConvertedObjectCache[PyObjectUtils::builtin_id(pyObject)] = pureInstance;

    return pureInstance;
    }


void PyObjectWalker::_walkPyObject(PyObject* pyObject, int64_t objectId) {
    if (PyObject_IsInstance(pyObject, mRemotePythonObjectClass))
        {
        _registerRemotePythonObject(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mPackedHomogenousDataClass))
        {
        _registerPackedHomogenousData(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mFutureClass))
        {
        _registerFuture(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, PyExc_Exception)
            and _classIsNamedSingleton(pyObject))
        {
        _registerBuiltinExceptionInstance(objectId, pyObject);
        }
    else if (_isTypeOrBuiltinFunctionAndInNamedSingletons(pyObject))
        {
        _registerTypeOrBuiltinFunctionNamedSingleton(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mTracebackType))
        {
        _registerStackTraceAsJson(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mWithBlockClass))
        {
        _registerWithBlock(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mUnconvertibleClass))
        {
        PyObject* objectThatsNotConvertible = PyObject_GetAttrString(
            pyObject,
            "objectThatsNotConvertible"
            );
        if (objectThatsNotConvertible == NULL) {
            throw std::runtime_error(
                "expected Unconvertible instances to have an "
                "`objectThatsNotConvertible` member"
                );
            }

        _registerUnconvertible(objectId, objectThatsNotConvertible);

        Py_DECREF(objectThatsNotConvertible);
        }
    else if (PyTuple_Check(pyObject))
        {
        _registerTuple(objectId, pyObject);
        }
    else if (PyList_Check(pyObject))
        {
        _registerList(objectId, pyObject);
        }
    else if (PyDict_Check(pyObject))
        {
        _registerDict(objectId, pyObject);
        }
    else if (_isPrimitive(pyObject))
        {
        _registerPrimitive(objectId, pyObject);
        }
    else if (PyFunction_Check(pyObject))
        {
        _registerFunction(objectId, pyObject);
        }
    else if (PyforaInspect::isclass(pyObject))
        {
        _registerClass(objectId, pyObject);
        }
    else if (PyMethod_Check(pyObject))
        {
        _registerInstanceMethod(objectId, pyObject);
        }
    else if (PyforaInspect::isclassinstance(pyObject))
        {
        _registerClassInstance(objectId, pyObject);
        }
    else {
        throw std::runtime_error("PyObjectWalker couldn't handle a PyObject: " +
            PyObjectUtils::repr_string(pyObject));
        }
    }


bool PyObjectWalker::_isPrimitive(const PyObject* pyObject)
    {
    return Py_None == pyObject or
        PyInt_Check(pyObject) or
        PyFloat_Check(pyObject) or
        PyString_Check(pyObject) or
        PyBool_Check(pyObject);        
    }


bool PyObjectWalker::_allPrimitives(const PyObject* pyList)
    {
    // precondition: the argument must be a PyList
    Py_ssize_t size = PyList_GET_SIZE(pyList);
    for (Py_ssize_t ix = 0; ix < size; ++ix)
        {
        if (not _isPrimitive(PyList_GET_ITEM(pyList, ix)))
            return false;
        }
    return true;
    }


bool PyObjectWalker::_classIsNamedSingleton(PyObject* pyObject) const
    {
    PyObject* __class__attr = PyObject_GetAttrString(pyObject, "__class__");

    if (__class__attr == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "arguments to this function are expected to have a ");
        }

    bool tr = (mPythonSingletonToName.find(__class__attr) != 
        mPythonSingletonToName.end());

    Py_DECREF(__class__attr);

    return tr;
    }


void PyObjectWalker::_registerUnconvertible(int64_t objectId,
                                            const PyObject* pyObject) const
    {
    PyObject* modulePathOrNone = _getModulePathForObject(pyObject);
    if (modulePathOrNone == NULL) {
        throw std::runtime_error("error getting modulePathOrNone");
        }

    mObjectRegistry.defineUnconvertible(objectId, modulePathOrNone);

    Py_DECREF(modulePathOrNone);
    }


void PyObjectWalker::_registerRemotePythonObject(int64_t objectId,
                                                 PyObject* pyObject) const
    {
    PyObject* _pyforaComputedValueArg_attr = PyObject_GetAttrString(
        pyObject,
        "_pyforaComputedValueArg"
        );
    if (_pyforaComputedValueArg_attr == NULL) {
        throw std::runtime_error(
            "py error getting _pyforaComputedValueArg "
            "in PyObjectWalker::_registerRemotePythonObject: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        _pyforaComputedValueArg_attr,
        NULL
        );
    
    Py_DECREF(_pyforaComputedValueArg_attr);

    if (res == NULL) {
        throw std::runtime_error(
            "py error calling _pyforaComputedValueArg "
            "in PyObjectWalker::_registerRemotePythonObject: " +
            PyObjectUtils::exc_string()
            );
        }

    mObjectRegistry.defineRemotePythonObject(
        objectId,
        res
        );

    Py_DECREF(res);
    }


void PyObjectWalker::_registerPackedHomogenousData(int64_t objectId,
                                                   PyObject* pyObject) const
    {
    mObjectRegistry.definePackedHomogenousData(objectId, pyObject);
    }


void PyObjectWalker::_registerFuture(int64_t objectId, PyObject* pyObject)
    {
    PyObject* result_attr = PyObject_GetAttrString(pyObject, "result");
    if (result_attr == NULL) {
        PyErr_Print();
        throw std::runtime_error("expected a result member on Future.Future instances");
        }

    PyObject* res = PyObject_CallFunctionObjArgs(result_attr, NULL);

    Py_DECREF(result_attr);

    if (res == NULL) {
        throw std::runtime_error(
            "py error calling future.result in "
            "PyObjectWalker::_registerFuture: " +
            PyObjectUtils::exc_string()
            );
        }

    _walkPyObject(res, objectId);

    Py_DECREF(res);
    }


void PyObjectWalker::_registerBuiltinExceptionInstance(int64_t objectId,
                                                       PyObject* pyException)
    {
    PyObject* __class__attr = PyObject_GetAttrString(pyException, "__class__");

    if (__class__attr == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "expected this PyObject to have a `__class__` attr");
        }

    std::map<PyObject*, std::string>::const_iterator it =
        mPythonSingletonToName.find(__class__attr);
    Py_DECREF(__class__attr);
    if (it == mPythonSingletonToName.end()) {
        throw std::runtime_error(
            "it's supposed to be a precondition to this function that this not happen");
        }

    PyObject* args_attr = PyObject_GetAttrString(pyException, "args");
    if (args_attr == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "expected this PyObject to have an `args` attr");
        }

    int64_t argsId = walkPyObject(args_attr);

    Py_DECREF(args_attr);

    mObjectRegistry.defineBuiltinExceptionInstance(objectId,
                                                   it->second,
                                                   argsId);
    }


bool PyObjectWalker::_isTypeOrBuiltinFunctionAndInNamedSingletons(PyObject* pyObject) const
    {
    if (not PyType_Check(pyObject) and not PyCFunction_Check(pyObject)) {
        return false;
        }

    return mPythonSingletonToName.find(pyObject) != mPythonSingletonToName.end();
    }


std::string PyObjectWalker::_fileText(const PyObject* fileNamePyObj) const
    {
    PyObject* lines = PyforaInspect::getlines(fileNamePyObj);
    if (lines == NULL) {
        throw std::runtime_error(
            "error calling getlines");
        }
    
    if (not PyList_Check(lines)) {
        Py_DECREF(lines);
        throw std::runtime_error("expected a list");
        }

    std::ostringstream oss;
    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(lines); ++ix)
        {
        PyObject* item = PyList_GET_ITEM(lines, ix);
        
        if (PyString_Check(item)) {
            oss.write(PyString_AS_STRING(item), PyString_GET_SIZE(item));
            }
        else if (PyUnicode_Check(item)) {
            PyObject* pyString = PyUnicode_AsASCIIString(item);
            if (pyString == NULL) {
                throw std::runtime_error("error getting string from unicode: " + 
                    PyObjectUtils::exc_string());
                }

            oss.write(PyString_AS_STRING(pyString), PyString_GET_SIZE(pyString));

            Py_DECREF(pyString);
            }
        else {
            Py_DECREF(lines);
            throw std::runtime_error("all elements in lines should be str or unicode");
            }

        }
    
    Py_DECREF(lines);

    return oss.str();
    }


std::string PyObjectWalker::_fileText(const std::string& filename) const
    {
    PyObject* fileNamePyObj = PyString_FromStringAndSize(filename.data(),
                                                         filename.size());
    if (fileNamePyObj == NULL) {
        throw std::runtime_error("couldn't create a python string out of a std::string");
        }

    std::string tr =  _fileText(fileNamePyObj);

    Py_DECREF(fileNamePyObj);

    return tr;
    }


PyObject* PyObjectWalker::_getModulePathForObject(const PyObject* pyObject) const
    {
    PyObject* tr =PyObject_CallFunctionObjArgs(
        mGetPathToObjectFun,
        pyObject,
        NULL);
    if (tr == NULL) {
        throw std::runtime_error("hit an unexpected error calling getPathToObject: " +
            PyObjectUtils::exc_string());
        }
    return tr;
    }


void PyObjectWalker::_registerTypeOrBuiltinFunctionNamedSingleton(int64_t objectId,
                                                                  PyObject* pyObject) const
    {
    std::map<PyObject*, std::string>::const_iterator it =
        mPythonSingletonToName.find(pyObject);

    if (it == mPythonSingletonToName.end()) {
        throw std::runtime_error(
            "this shouldn't happen if _isTypeOrBuiltinFunctionAndInNamedSingletons "
            "returned true"
            );
        }

    mObjectRegistry.defineNamedSingleton(objectId, it->second);
    }


namespace {

int64_t _getWithBlockLineNumber(PyObject* withBlock)
    {
    int64_t lineno;
    PyObject* pyLineNumber = PyObject_GetAttrString(withBlock, "lineNumber");
    if (pyLineNumber == NULL) {
        throw std::runtime_error("error getting lineNumber attr in _registerWithBlock");
        }
    if (not PyInt_Check(pyLineNumber)) {
        PyErr_Print();
        Py_DECREF(pyLineNumber);
        throw std::runtime_error("expected lineNumber to be an int");
        }
    lineno = PyInt_AS_LONG(pyLineNumber);
    Py_DECREF(pyLineNumber);

    return lineno;
    }



void _handleUnresolvedFreeVariableException(const PyObject* filename)
    {
    PyObject * exception, * v, * tb;

    PyErr_Fetch(&exception, &v, &tb);
    if (exception == NULL) {
        throw std::runtime_error("expected an Exception to be set.");
        }

    PyErr_NormalizeException(&exception, &v, &tb);

    if (PyObject_IsInstance(
            v,
            UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionClass()))
        {
        PyObject* unresolvedFreeVariableExceptionWithTrace =
            UnresolvedFreeVariableExceptions::getUnresolvedFreeVariableExceptionWithTrace(
                v,
                filename
                );
        if (unresolvedFreeVariableExceptionWithTrace == NULL) {
            Py_DECREF(exception);
            Py_DECREF(v);
            Py_DECREF(tb);
            throw std::runtime_error(
                "py error getting "
                "unresolvedFreeVariableExceptionWithTrace in "
                "PyObjectWalker::<anonymous namespace>::"
                "_handleUnresolvedFreeVariableException: " +
                PyObjectUtils::exc_string()
                );
            }
        
        throw UnresolvedFreeVariableExceptionWithTrace(
            unresolvedFreeVariableExceptionWithTrace
            );
        }
    else {
        PyErr_Restore(exception, v, tb);
        throw std::runtime_error(
            "PyObjectWalker::<anonymous namespace>::"
            "_handleUnresolvedFreeVariableException: " +
            PyObjectUtils::format_exc());
        }

    Py_DECREF(exception);
    Py_DECREF(v);
    Py_DECREF(tb);
    }


}


PyObject* PyObjectWalker::_pythonTracebackToJson(const PyObject* pyObject) const
    {
    return PyObject_CallFunctionObjArgs(
        mPythonTracebackToJsonFun,
        pyObject,
        NULL);
    }


void
PyObjectWalker::_registerStackTraceAsJson(int64_t objectId,
                                          const PyObject* pyObject) const
    {
    PyObject* pythonTraceBackAsJson = _pythonTracebackToJson(pyObject);
    if (pythonTraceBackAsJson == NULL) {
        throw std::runtime_error(
            "py error in PyObjectWalker:_registerStackTraceAsJson: " +
            PyObjectUtils::exc_string()
            );
        }

    mObjectRegistry.defineStacktrace(objectId, pythonTraceBackAsJson);

    Py_DECREF(pythonTraceBackAsJson);
    }


void PyObjectWalker::_registerWithBlock(int64_t objectId, PyObject* pyObject)
    {
    int64_t lineno = _getWithBlockLineNumber(pyObject);

    PyObject* withBlockFun = _withBlockFun(pyObject, lineno);
    if (withBlockFun == NULL) {
        throw std::runtime_error(
            "error getting with block ast functionDef"
            " in PyObjectWalker::_registerWithBlock: " +
            PyObjectUtils::exc_string());
        }
    if (PyAstUtil::hasReturnInOuterScope(withBlockFun)) {
        std::ostringstream err_oss;
        err_oss << "return statement not supported in pyfora with-block (line ";
        err_oss << PyAstUtil::getReturnLocationsInOuterScope(withBlockFun);
        err_oss << ")";

        Py_DECREF(withBlockFun);

        throw BadWithBlockError(err_oss.str());
        }
    if (PyAstUtil::hasYieldInOuterScope(withBlockFun)) {
        std::ostringstream err_oss;
        err_oss << "yield expression not supported in pyfora with-block (line ";
        err_oss << PyAstUtil::getYieldLocationsInOuterScope(withBlockFun);
        err_oss << ")";

        Py_DECREF(withBlockFun);

        throw BadWithBlockError(err_oss.str());
        }

    PyObject* chainsWithPositions = _freeMemberAccessChainsWithPositions(withBlockFun);
    if (chainsWithPositions == NULL) {
        Py_DECREF(withBlockFun);
        throw std::runtime_error(
            "py error getting freeMemberAccessChainsWithPositions "
            "in PyObjectWalker::_registerWithBlock: "+
            PyObjectUtils::exc_string());
        }

    PyObject* boundVariables = PyObject_GetAttrString(pyObject, "boundVariables");
    if (boundVariables == NULL) {
        PyErr_Print();
        Py_DECREF(chainsWithPositions);
        Py_DECREF(withBlockFun);
        throw std::runtime_error("couldn't get boundVariables attr");
        }

    _augmentChainsWithBoundValuesInScope(
        pyObject,
        withBlockFun,
        boundVariables,
        chainsWithPositions);

    Py_DECREF(withBlockFun);
    
    PyObject* pyConvertedObjectCache = _getPyConvertedObjectCache();
    if (pyConvertedObjectCache == NULL) {
        PyErr_Print();
        Py_DECREF(boundVariables);
        Py_DECREF(chainsWithPositions);
        throw std::runtime_error("error getting pyConvertedObjectCache");
        }

    PyObject* resolutions =
        mFreeVariableResolver.resolveFreeVariableMemberAccessChains(
            chainsWithPositions,
            boundVariables,
            pyConvertedObjectCache);

    Py_DECREF(pyConvertedObjectCache);
    Py_DECREF(boundVariables);
    Py_DECREF(chainsWithPositions);

    PyObject* filename = PyObject_GetAttrString(pyObject, "sourceFileName");
    if (filename == NULL) {
        Py_XDECREF(resolutions);
        throw std::runtime_error(
            "py error getting sourceFileName attr "
            "in PyObjectWalker::_registerWithBlock: "
            + PyObjectUtils::exc_string()
            );
        }

    if (resolutions == NULL) {
        _handleUnresolvedFreeVariableException(filename);
        }

    std::map<FreeVariableMemberAccessChain, int64_t> processedResolutions =
        _processFreeVariableMemberAccessChainResolutions(resolutions);

    Py_DECREF(resolutions);

    int64_t sourceFileId = walkFileDescription(
        FileDescription::cachedFromArgs(
            PyObjectUtils::std_string(filename),
            _fileText(filename)
            )
        );

    Py_DECREF(filename);

    mObjectRegistry.defineWithBlock(
        objectId,
        processedResolutions,
        sourceFileId,
        lineno);
    }


void PyObjectWalker::_augmentChainsWithBoundValuesInScope(
        PyObject* pyObject,
        PyObject* withBlockFun,
        PyObject* boundVariables,
        PyObject* chainsWithPositions) const
    {
    if (not PySet_Check(chainsWithPositions)) {
        throw std::runtime_error("expected chainsWithPositions to be a set");
        }
    
    PyObject* boundValuesInScopeWithPositions =
        PyAstFreeVariableAnalyses::collectBoundValuesInScope(withBlockFun, true);
    if (boundValuesInScopeWithPositions == NULL) {
        PyErr_Print();
        throw std::runtime_error("error calling collectBoundValuesInScope");
        }

    PyObject* unboundLocals = PyObject_GetAttrString(pyObject, "unboundLocals");
    if (unboundLocals == NULL) {
        Py_DECREF(boundValuesInScopeWithPositions);
        throw std::runtime_error("couldn't get unboundLocals attr");
        }

    PyObject* iterator = PyObject_GetIter(boundValuesInScopeWithPositions);
    if (iterator == NULL) {
        PyErr_Print();
        Py_DECREF(unboundLocals);
        Py_DECREF(boundValuesInScopeWithPositions);
        throw std::runtime_error("error calling iter");
        }    
    PyObject* item = NULL;
    while((item = PyIter_Next(iterator)) != NULL) {
        if (!PyTuple_Check(item)) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            Py_DECREF(unboundLocals);
            Py_DECREF(boundValuesInScopeWithPositions);
            throw std::runtime_error("expected items to be tuples");
            }
        if (PyTuple_GET_SIZE(item) != 2) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            Py_DECREF(unboundLocals);
            Py_DECREF(boundValuesInScopeWithPositions);
            throw std::runtime_error("expected items to be length-two tuples");
            }

        PyObject* val = PyTuple_GET_ITEM(item, 0);
        PyObject* pos = PyTuple_GET_ITEM(item, 1);

        if (not PyObjectUtils::in(unboundLocals, val) and 
                PyObjectUtils::in(boundVariables, val))
            {
            PyObject* varWithPosition = 
                PyAstFreeVariableAnalyses::varWithPosition(val, pos);
            if (varWithPosition == NULL) {
                Py_DECREF(item);
                Py_DECREF(iterator);
                Py_DECREF(unboundLocals);
                Py_DECREF(boundValuesInScopeWithPositions);
                throw std::runtime_error("couldn't get VarWithPosition");
                }
            if (PySet_Add(chainsWithPositions, varWithPosition) != 0) {
                Py_DECREF(varWithPosition);
                Py_DECREF(item);
                Py_DECREF(iterator);
                Py_DECREF(unboundLocals);
                Py_DECREF(boundValuesInScopeWithPositions);
                throw std::runtime_error("error adding to a set");
                }
            Py_DECREF(varWithPosition);
            }
        }

    Py_XDECREF(item);
    Py_DECREF(iterator);
    Py_DECREF(unboundLocals);
    Py_DECREF(boundValuesInScopeWithPositions);
    }


void PyObjectWalker::_registerTuple(int64_t objectId, PyObject* pyTuple)
    {
    std::vector<int64_t> memberIds;
    Py_ssize_t size = PyTuple_GET_SIZE(pyTuple);
    for (Py_ssize_t ix = 0; ix < size; ++ix)
        {
        memberIds.push_back(
            walkPyObject(PyTuple_GET_ITEM(pyTuple, ix))
            );
        }

    mObjectRegistry.defineTuple(objectId, memberIds);
    }
    

void PyObjectWalker::_registerList(int64_t objectId, PyObject* pyList)
    {
    if (_allPrimitives(pyList))
        {
        _registerListOfPrimitives(objectId, pyList);
        }
    else {
        _registerListGeneric(objectId, pyList);
        }
    }


void PyObjectWalker::_registerListOfPrimitives(int64_t objectId, PyObject* pyList) const
    {
    mObjectRegistry.definePrimitive(objectId, pyList);
    }


void PyObjectWalker::_registerListGeneric(int64_t objectId, const PyObject* pyList)
    {
    std::vector<int64_t> memberIds;
    Py_ssize_t size = PyList_GET_SIZE(pyList);
    for (Py_ssize_t ix = 0; ix < size; ++ix)
        {
        memberIds.push_back(
            walkPyObject(PyList_GET_ITEM(pyList, ix))
            );
        }
    mObjectRegistry.defineList(objectId, memberIds);
    }
    

void PyObjectWalker::_registerDict(int64_t objectId, PyObject* pyDict)
    {
    std::vector<int64_t> keyIds;
    std::vector<int64_t> valueIds;
    PyObject* key = NULL;
    PyObject* value = NULL;
    Py_ssize_t pos = 0;
    
    while (PyDict_Next(pyDict, &pos, &key, &value)) {
        keyIds.push_back(walkPyObject(key));
        valueIds.push_back(walkPyObject(value));
        }

    mObjectRegistry.defineDict(objectId, keyIds, valueIds);
    }
    

void PyObjectWalker::_registerFunction(int64_t objectId, PyObject* pyObject)
    {
    ClassOrFunctionInfo info = _classOrFunctionInfo(pyObject, true);
    
    mObjectRegistry.defineFunction(
        objectId,
        info.sourceFileId(),
        info.lineNumber(),
        info.freeVariableMemberAccessChainsToId()
        );
    }


namespace {

// precondition: obj should be a function or class
void _checkForInlineForaName(PyObject* obj) {
    PyObject* __name__attr = PyObject_GetAttrString(obj, "__name__");
    if (__name__attr == NULL) {
        throw std::runtime_error(
            "expected to find a __name__attr "
            "in PyObjectWalker::<anonymous namespace>::"
            "_checkForInlineForaName: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyString_Check(__name__attr)) {
        Py_DECREF(__name__attr);
        throw std::runtime_error(
            "expected __name__ attr to be a string"
            );
        }
    
    std::string __name__attr_as_string = std::string(
        PyString_AS_STRING(__name__attr),
        PyString_GET_SIZE(__name__attr)
        );

    Py_DECREF(__name__attr);

    if (__name__attr_as_string == "__inline_fora") {
        throw PythonToForaConversionError("in pfora, `__inline_fora` is a reserved word");
        }
    }

}


ClassOrFunctionInfo
PyObjectWalker::_classOrFunctionInfo(PyObject* obj, bool isFunction)
    {
    // old PyObjectWalker checks for __inline_fora here
    _checkForInlineForaName(obj);

    // should probably make these just return PyStrings, as 
    // we only repackage these into PyStrings anyway
    PyObject* textAndFilename = PyAstUtil::sourceFilenameAndText(obj);
    if (textAndFilename == NULL) {
        throw std::runtime_error(
            "error calling sourceFilenameAndText: " + PyObjectUtils::exc_string()
            );
        }
    if (not PyTuple_Check(textAndFilename)) {
        Py_DECREF(textAndFilename);
        throw std::runtime_error("expected sourceFilenameAndText to return a tuple");
        }
    if (PyTuple_GET_SIZE(textAndFilename) != 2) {
        Py_DECREF(textAndFilename);
        throw std::runtime_error(
            "expected sourceFilenameAndText to return a tuple of length 2"
            );
        }
    
    // borrowed reference
    PyObject* text = PyTuple_GET_ITEM(textAndFilename, 0);
    // borrowed reference
    PyObject* filename = PyTuple_GET_ITEM(textAndFilename, 1);

    long startingSourceLine = PyAstUtil::startingSourceLine(obj);
    PyObject* sourceAst = PyAstUtil::pyAstFromText(text);
    if (sourceAst == NULL) {
        Py_DECREF(textAndFilename);
        throw std::runtime_error(
            "an error occured calling pyAstFromText: " + PyObjectUtils::exc_string()
            + "\nfilename = " + PyObjectUtils::str_string(filename)
            + "\ntext = " + PyObjectUtils::str_string(text)
            );
        }

    PyObject* pyAst = NULL;
    if (isFunction) {
        pyAst = PyAstUtil::functionDefOrLambdaAtLineNumber(
            sourceAst,
            startingSourceLine);
        }
    else {
        pyAst = PyAstUtil::classDefAtLineNumber(sourceAst,
                                                startingSourceLine);
        }

    Py_DECREF(sourceAst);

    if (pyAst == NULL) {
        PyErr_Print();
        throw std::runtime_error("an error occured getting the sub-ast.");
        }

    PyObject* resolutions =
        _computeAndResolveFreeVariableMemberAccessChainsInAst(obj, pyAst);

    Py_DECREF(pyAst);

    if (resolutions == NULL) {
        _handleUnresolvedFreeVariableException(filename);
        }

    std::map<FreeVariableMemberAccessChain, int64_t> processedResolutions =
        _processFreeVariableMemberAccessChainResolutions(resolutions);

    Py_DECREF(resolutions);

    int64_t fileId = walkFileDescription(
        FileDescription::cachedFromArgs(
            PyObjectUtils::std_string(filename),
            PyObjectUtils::std_string(text)
            )
        );

    Py_DECREF(textAndFilename);

    return ClassOrFunctionInfo(fileId,
                               startingSourceLine,
                               processedResolutions);
    }


std::map<FreeVariableMemberAccessChain, int64_t>
PyObjectWalker::_processFreeVariableMemberAccessChainResolutions(
        PyObject* resolutions
        )
    {
    if (not PyDict_Check(resolutions)) {
        throw std::runtime_error("expected a dict argument");
        }

    PyObject * key, * value;
    Py_ssize_t pos = 0;
    std::map<FreeVariableMemberAccessChain, int64_t> tr;

    while (PyDict_Next(resolutions, &pos, &key, &value)) {
        /*
          Values should be length-two tuples: (resolution, location)
         */
        if (not PyTuple_Check(value)) {
            throw std::runtime_error("expected tuple values");
            }
        if (PyTuple_GET_SIZE(value) != 2) {
            throw std::runtime_error("expected values to be tuples of length 2");
            }
        PyObject* resolution = PyTuple_GET_ITEM(value, 0);
        
        int64_t resolutionId = walkPyObject(resolution);
        tr[toChain(key)] = resolutionId;
        }

    return tr;
    }


PyObject* PyObjectWalker::_getPyConvertedObjectCache() const
    {
    PyObject* tr = PyDict_New();
    if (tr == NULL) {
        return NULL;
        }

    for (std::map<long, PyObject*>::const_iterator it =
             mConvertedObjectCache.begin();
         it != mConvertedObjectCache.end();
         ++it)
        {
        PyObject* pyLong = PyLong_FromLong(it->first);
        if (pyLong == NULL) {
            Py_DECREF(tr);
            throw std::runtime_error("error getting python long from C long");
            }

        if (PyDict_SetItem(tr, pyLong, it->second) != 0) {
            return NULL;
            }

        Py_DECREF(pyLong);
        }

    return tr;
    }


PyObject* PyObjectWalker::_computeAndResolveFreeVariableMemberAccessChainsInAst(
        const PyObject* pyObject,
        const PyObject* pyAst
        ) const
    {
    PyObject* chainsWithPositions = _freeMemberAccessChainsWithPositions(pyAst);
    if (chainsWithPositions == NULL) {
        return NULL;
        }

    PyObject* pyConvertedObjectCache = _getPyConvertedObjectCache();
    if (pyConvertedObjectCache == NULL) {
        Py_DECREF(chainsWithPositions);
        return NULL;
        }

    PyObject* resolutions = 
        mFreeVariableResolver.resolveFreeVariableMemberAccessChainsInAst(
            pyObject,
            pyAst,
            chainsWithPositions,
            pyConvertedObjectCache);

    Py_DECREF(pyConvertedObjectCache);
    Py_DECREF(chainsWithPositions);

    return resolutions;
    }


PyObject* PyObjectWalker::_freeMemberAccessChainsWithPositions(
        const PyObject* pyAst
        ) const
    {
    return PyAstFreeVariableAnalyses::getFreeMemberAccessChainsWithPositions(
            pyAst,
            false,
            true,
            mExcludePredicateFun
            );
    }


void PyObjectWalker::_registerClass(int64_t objectId, PyObject* pyObject)
    {
    ClassOrFunctionInfo info = _classOrFunctionInfo(pyObject, false);

    PyObject* bases = PyObject_GetAttrString(pyObject,
                                             "__bases__");

    if (bases == NULL) {
        throw std::runtime_error(
            "couldn't get __bases__ member of an object we expected to be a class"
            );
        }
    if (not PyTuple_Check(bases)) {
        Py_DECREF(bases);
        throw std::runtime_error("expected bases to be a list");
        }

    std::vector<int64_t> baseClassIds;
    for (Py_ssize_t ix = 0; ix < PyTuple_GET_SIZE(bases); ++ix)
        {
        PyObject* item = PyTuple_GET_ITEM(bases, ix);

        std::map<PyObject*, int64_t>::const_iterator it =
            mPyObjectToObjectId.find(item);
        
        if (it == mPyObjectToObjectId.end()) {
            Py_DECREF(bases);
            throw std::runtime_error(
                "expected each base class to have a registered id"
                ". class = " + PyObjectUtils::str_string(pyObject));
            }
        
        baseClassIds.push_back(it->second);
        }

    Py_DECREF(bases);

    mObjectRegistry.defineClass(
        objectId,
        info.sourceFileId(),
        info.lineNumber(),
        info.freeVariableMemberAccessChainsToId(),
        baseClassIds);

    }


void PyObjectWalker::_registerClassInstance(int64_t objectId, PyObject* pyObject)
    {
    PyObject* classObject = PyObject_GetAttrString(pyObject, "__class__");
    if (classObject == NULL) {
        PyErr_Print();
        throw std::runtime_error(
            "couldn't get __class__ attr on a pyObject we thought had that attr"
            );
        }

    int64_t classId = walkPyObject(classObject);

    if (mObjectRegistry.isUnconvertible(classId)) {
        mObjectRegistry.defineUnconvertible(objectId,
            _getModulePathForObject(pyObject)
            );
        return;
        }

    PyObject* dataMemberNames = _getDataMemberNames(pyObject, classObject);
    if (dataMemberNames == NULL) {
        Py_DECREF(classObject);
        throw std::runtime_error("error in _registerClassInstance:" +
            PyObjectUtils::exc_string()
            );
        }

    Py_DECREF(classObject);

    if (not PyList_Check(dataMemberNames)) {
        throw std::runtime_error("expected dataMemberNames to be a list");
        }

    std::map<std::string, int64_t> classMemberNameToClassMemberId;

    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(dataMemberNames); ++ix)
        {
        PyObject* dataMemberName = PyList_GET_ITEM(dataMemberNames, ix);
        if (not PyString_Check(dataMemberName)) {
            throw std::runtime_error("expected data member names to be strings");
            }

        PyObject* dataMember = PyObject_GetAttr(pyObject, dataMemberName);
        if (dataMember == NULL) {
            PyErr_Print();
            throw std::runtime_error("error getting datamember");
            }

        int64_t dataMemberId = walkPyObject(dataMember);

        classMemberNameToClassMemberId[
            std::string(
                PyString_AS_STRING(dataMemberName),
                PyString_GET_SIZE(dataMemberName)
                )
            ] = dataMemberId;

        Py_DECREF(dataMember);
        }
    
    Py_DECREF(dataMemberNames);

    mObjectRegistry.defineClassInstance(
        objectId,
        classId,
        classMemberNameToClassMemberId);
    }


PyObject*
PyObjectWalker::_getDataMemberNames(PyObject* pyObject, PyObject* classObject) const
    {
    if (PyObject_HasAttrString(pyObject, "__dict__")) {
        PyObject* __dict__attr = PyObject_GetAttrString(pyObject, "__dict__");
        if (__dict__attr == NULL) {
            return NULL;
            }
        if (not PyDict_Check(__dict__attr)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected __dict__ attr to be a dict"
                );
            return NULL;
            }
        PyObject* keys = PyDict_Keys(__dict__attr);
        Py_DECREF(__dict__attr);
        if (keys == NULL) {
            return NULL;
            }
        if (not PyList_Check(keys)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected keys to be a list"
                );
            return NULL;
            }

        return keys;
        }
    else {
        return PyAstUtil::collectDataMembersSetInInit(classObject);
        }
    }


PyObject* PyObjectWalker::_withBlockFun(PyObject* withBlock, int64_t lineno) const
    {
    PyObject* sourceText = PyObject_GetAttrString(withBlock, "sourceText");
    if (sourceText == NULL) {
        return NULL;
        }

    PyObject* sourceTree = PyAstUtil::pyAstFromText(sourceText);
    Py_DECREF(sourceText);
    if (sourceTree == NULL) {
        return NULL;
        }

    PyObject* withBlockAst = PyAstUtil::withBlockAtLineNumber(sourceTree, lineno);
    Py_DECREF(sourceTree);
    if (withBlockAst == NULL) {
        return NULL;
        }

    PyObject* body = PyObject_GetAttrString(withBlockAst, "body");
    Py_DECREF(withBlockAst);
    if (body == NULL) {
        return NULL;
        }

    PyObject* argsTuple = Py_BuildValue("()");
    if (argsTuple == NULL) {
        Py_DECREF(body);
        return NULL;
        }

    PyObject* ast_args = _defaultAstArgs();
    if (ast_args == NULL) {
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return NULL;
        }
    
    PyObject* decorator_list = PyList_New(0);
    if (decorator_list == NULL) {
        Py_DECREF(ast_args);
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return NULL;
        }

    PyObject* kwds = Py_BuildValue("{s:s, s:O, s:O, s:O, s:i, s:i}",
        "name", "",
        "args", ast_args,
        "body", body,
        "decorator_list", decorator_list,
        "lineno", lineno,
        "col_offset", 0);
    if (kwds == NULL) {
        Py_DECREF(decorator_list);
        Py_DECREF(ast_args);
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return NULL;
        }
        
    PyObject* res = Ast::FunctionDef(argsTuple, kwds);

    Py_DECREF(kwds);
    Py_DECREF(decorator_list);
    Py_DECREF(kwds);
    Py_DECREF(ast_args);
    Py_DECREF(argsTuple);
    Py_DECREF(body);

    return res;
    }


PyObject* PyObjectWalker::_defaultAstArgs() const
    {
    PyObject* args = Py_BuildValue("()");
    if (args == NULL) {
        return NULL;
        }

    PyObject* emptyList = PyList_New(0);
    if (emptyList == NULL) {
        Py_DECREF(args);
        return NULL;
        }

    PyObject* kwargs = Py_BuildValue("{sOsOssss}",
        "args", emptyList,
        "defaults", emptyList,
        "kwarg", NULL,
        "vararg", NULL);
    if (kwargs == NULL) {
        Py_DECREF(emptyList);
        Py_DECREF(args);
        return NULL;
        }
    
    PyObject* res = Ast::arguments(args, kwargs);

    Py_DECREF(kwargs);
    Py_DECREF(emptyList);
    Py_DECREF(args);

    if (res == NULL) {
        return NULL;
        }

    return res;
    }


void PyObjectWalker::_registerInstanceMethod(int64_t objectId, PyObject* pyObject)
    {
    PyObject* __self__attr = PyObject_GetAttrString(pyObject, "__self__");
    if (__self__attr == NULL) {
        throw std::runtime_error(
            "expected to have a __self__ attr on instancemethods"
            );
        }

    PyObject* __name__attr = PyObject_GetAttrString(pyObject, "__name__");
    if (__name__attr == NULL) {
        Py_DECREF(__self__attr);
        throw std::runtime_error(
            "expected to have a __name__ attr on instancemethods"
            );
        }
    if (not PyString_Check(__name__attr)) {
        Py_DECREF(__name__attr);
        Py_DECREF(__self__attr);
        throw std::runtime_error(
            "expected __name__ attr to be a string"
            );
        }

    int64_t instanceId = walkPyObject(__self__attr);

    mObjectRegistry.defineInstanceMethod(objectId,
                                         instanceId,
                                         PyObjectUtils::std_string(__name__attr)
                                         );

    Py_DECREF(__name__attr);
    Py_DECREF(__self__attr);
    }


FreeVariableMemberAccessChain PyObjectWalker::toChain(const PyObject* obj)
    {
    if (not PyTuple_Check(obj)) {
        throw std::runtime_error("expected FVMAC to be tuples ");
        }

    std::vector<std::string> variables;

    for (Py_ssize_t ix = 0; ix < PyTuple_GET_SIZE(obj); ++ix) {
        PyObject* item = PyTuple_GET_ITEM(obj, ix);
        if (not PyString_Check(item)) {
            throw std::runtime_error("expected FVMAC elements to be strings");
            }
        variables.push_back(PyObjectUtils::std_string(item));
        }

    return FreeVariableMemberAccessChain(variables);
    }
