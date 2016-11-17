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

#include <stdexcept>
#include <vector>


namespace {

bool _isPrimitive(const PyObject* pyObject)
    {
    return Py_None == pyObject or
        PyInt_Check(pyObject) or
        PyFloat_Check(pyObject) or
        PyString_Check(pyObject) or
        PyBool_Check(pyObject);        
    }


bool _allPrimitives(const PyObject* pyList)
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

} // anonymous namespace


PyObjectWalker::PyObjectWalker(
        PyObject* purePythonClassMapping,
        BinaryObjectRegistry& objectRegistry,
        PyObject* excludePredicateFun,
        PyObject* excludeList,
        PyObject* terminalValueFilter,
        PyObject* traceback_type,
        PyObject* pythonTracebackToJsonFun) :
            mPureImplementationMappings(purePythonClassMapping),
            mRemotePythonObjectClass(nullptr),
            mPackedHomogenousDataClass(nullptr),
            mFutureClass(nullptr),
            mExcludePredicateFun(excludePredicateFun),
            mExcludeList(excludeList),
            mTerminalValueFilter(terminalValueFilter),
            mWithBlockClass(nullptr),
            mUnconvertibleClass(nullptr),
            mPyforaConnectHack(nullptr),
            mTracebackType(traceback_type),
            mPythonTracebackToJsonFun(pythonTracebackToJsonFun),
            mModuleLevelObjectIndex(ModuleLevelObjectIndex::get()),
            mObjectRegistry(objectRegistry),
            mFreeVariableResolver(excludeList, terminalValueFilter)
    {
    _initPythonSingletonToName();
    _initRemotePythonObjectClass();
    _initPackedHomogenousDataClass();
    _initFutureClass();
    _initWithBlockClass();
    _initUnconvertibleClass();
    _initPyforaConnectHack();
    }


void PyObjectWalker::_initWithBlockClass()
    {
    PyObject* withBlockModule = PyImport_ImportModule("pyfora.PyforaWithBlock");
    if (withBlockModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initWithBlockClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mWithBlockClass = PyObject_GetAttrString(withBlockModule, "PyforaWithBlock");
    Py_DECREF(withBlockModule);
    if (mWithBlockClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initWithBlockClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initFutureClass()
    {
    PyObject* futureModule = PyImport_ImportModule("pyfora.Future");
    if (futureModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initFutureClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mFutureClass = PyObject_GetAttrString(futureModule, "Future");
    Py_DECREF(futureModule);
    if (mFutureClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initFutureClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPackedHomogenousDataClass()
    {
    PyObject* typeDescriptionModule =
        PyImport_ImportModule("pyfora.TypeDescription");
    if (typeDescriptionModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPackedHomogenousDataClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mPackedHomogenousDataClass = PyObject_GetAttrString(typeDescriptionModule,
                                                        "PackedHomogenousData");
    Py_DECREF(typeDescriptionModule);
    if (mPackedHomogenousDataClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPackedHomogenousDataClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initRemotePythonObjectClass()
    {
    PyObject* remotePythonObjectModule =
        PyImport_ImportModule("pyfora.RemotePythonObject");
    if (remotePythonObjectModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initRemotePythonObjectClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mRemotePythonObjectClass = PyObject_GetAttrString(remotePythonObjectModule,
                                                      "RemotePythonObject");
    Py_DECREF(remotePythonObjectModule);
    if (mRemotePythonObjectClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initRemotePythonObjectClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPythonSingletonToName()
    {
    PyObject* namedSingletonsModule =
        PyImport_ImportModule("pyfora.NamedSingletons");    
    if (namedSingletonsModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* pythonSingletonToName = PyObject_GetAttrString(namedSingletonsModule,
                                                             "pythonSingletonToName");
    Py_DECREF(namedSingletonsModule);
    if (pythonSingletonToName == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyDict_Check(pythonSingletonToName)) {
        Py_DECREF(pythonSingletonToName);
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject * key, * value;
    Py_ssize_t pos = 0;
    char* string = nullptr;
    Py_ssize_t length = 0;

    while (PyDict_Next(pythonSingletonToName, &pos, &key, &value)) {
        if (PyString_AsStringAndSize(value, &string, &length) == -1) {
            throw std::runtime_error(
                "py err in PyObjectWalker::_initPythonSingletonToName: " +
                PyObjectUtils::exc_string()
                );
            }

        Py_INCREF(key);
        mPythonSingletonToName[key] = std::string(string, length);
        }

    Py_DECREF(pythonSingletonToName);
    }


void PyObjectWalker::_initUnconvertibleClass() {
    PyObject* unconvertibleModule = PyImport_ImportModule("pyfora.Unconvertible");
    if (unconvertibleModule == nullptr) {
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

    if (mUnconvertibleClass == nullptr) {
        throw std::runtime_error(
            "py error getting unconvertibleModule in "
            "PyObjectWalker::_initUnconvertibleClass " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPyforaConnectHack() {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    mPyforaConnectHack = PyObject_GetAttrString(pyforaModule, "connect");
    if (mPyforaConnectHack == nullptr) {
        throw std::runtime_error(
            "py error getting pyfora.connect in "
            "PyObjectWalker::_initPyforaConnectHack: " +
            PyObjectUtils::exc_string()
            );
        }
    }


PyObjectWalker::~PyObjectWalker()
    {
    for (const auto& p: mConvertedObjectCache) {
        Py_DECREF(p.second);
        }

    for (const auto& p: mPyObjectToObjectId) {
        Py_DECREF(p.first);
        }

    for (const auto& p: mPythonSingletonToName) {
        Py_DECREF(p.first);
        }

    Py_XDECREF(mPythonTracebackToJsonFun);
    Py_XDECREF(mTracebackType);
    Py_XDECREF(mPyforaConnectHack);
    Py_XDECREF(mUnconvertibleClass);
    Py_XDECREF(mWithBlockClass);
    Py_XDECREF(mTerminalValueFilter);
    Py_XDECREF(mExcludeList);
    Py_XDECREF(mExcludePredicateFun);
    Py_XDECREF(mFutureClass);
    Py_XDECREF(mPackedHomogenousDataClass);
    Py_XDECREF(mRemotePythonObjectClass);
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
        auto it = mPyObjectToObjectId.find(pyObject);

        if (it != mPyObjectToObjectId.end()) {
            return it->second;
            }
        }
    
        {
        auto it = mConvertedObjectCache.find(
            PyObjectUtils::builtin_id(pyObject)
            );

        if (it != mConvertedObjectCache.end()) {
            pyObject = it->second;
            }
        }

    bool wasReplaced = false;
    if (mPureImplementationMappings.canMap(pyObject)) {
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
    auto it = mConvertedFiles.find(fileDescription.filename);

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


PyObject* PyObjectWalker::_pureInstanceReplacement(const PyObject* pyObject)
    {
    PyObject* pureInstance = mPureImplementationMappings.mappableInstanceToPure(
        pyObject);
    if (pureInstance == nullptr) {
        return nullptr;
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
        if (objectThatsNotConvertible == nullptr) {
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


bool PyObjectWalker::_classIsNamedSingleton(PyObject* pyObject) const
    {
    PyObject* __class__attr = PyObject_GetAttrString(pyObject, "__class__");

    if (__class__attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_classIsNamedSingleton: " +
            PyObjectUtils::exc_string()
            );
        }

    bool tr = (mPythonSingletonToName.find(__class__attr) != 
        mPythonSingletonToName.end());

    Py_DECREF(__class__attr);

    return tr;
    }


void PyObjectWalker::_registerRemotePythonObject(int64_t objectId,
                                                 PyObject* pyObject) const
    {
    PyObject* _pyforaComputedValueArg_attr = PyObject_GetAttrString(
        pyObject,
        "_pyforaComputedValueArg"
        );
    if (_pyforaComputedValueArg_attr == nullptr) {
        throw std::runtime_error(
            "py error getting _pyforaComputedValueArg "
            "in PyObjectWalker::_registerRemotePythonObject: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(
        _pyforaComputedValueArg_attr,
        nullptr
        );
    
    Py_DECREF(_pyforaComputedValueArg_attr);

    if (res == nullptr) {
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


void PyObjectWalker::_registerUnconvertible(int64_t objectId,
                                            const PyObject* pyObject) const
    {
    PyObject* modulePathOrNone = 
        mModuleLevelObjectIndex.getPathToObject(pyObject);
    if (modulePathOrNone == nullptr) {
        throw std::runtime_error("error getting modulePathOrNone");
        }

    mObjectRegistry.defineUnconvertible(objectId, modulePathOrNone);

    Py_DECREF(modulePathOrNone);
    }


void PyObjectWalker::_registerPackedHomogenousData(int64_t objectId,
                                                   PyObject* pyObject) const
    {
    mObjectRegistry.definePackedHomogenousData(objectId, pyObject);
    }


void PyObjectWalker::_registerFuture(int64_t objectId, PyObject* pyObject)
    {
    PyObject* result_attr = PyObject_GetAttrString(pyObject, "result");
    if (result_attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerFuture: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* res = PyObject_CallFunctionObjArgs(result_attr, nullptr);

    Py_DECREF(result_attr);

    if (res == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerFuture: " +
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
    if (__class__attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerBuiltinExceptionInstance: " +
            PyObjectUtils::exc_string()
            );
        }

    auto it = mPythonSingletonToName.find(__class__attr);
    Py_DECREF(__class__attr);
    if (it == mPythonSingletonToName.end()) {
        throw std::runtime_error(
            "it's supposed to be a precondition to this function that this not happen");
        }

    PyObject* args_attr = PyObject_GetAttrString(pyException, "args");
    if (args_attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerBuiltinExceptionInstance: " +
            PyObjectUtils::exc_string()
            );
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
    if (lines == nullptr) {
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
            if (pyString == nullptr) {
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
    if (fileNamePyObj == nullptr) {
        throw std::runtime_error("couldn't create a python string out of a std::string");
        }

    std::string tr =  _fileText(fileNamePyObj);

    Py_DECREF(fileNamePyObj);

    return tr;
    }


void PyObjectWalker::_registerTypeOrBuiltinFunctionNamedSingleton(int64_t objectId,
                                                                  PyObject* pyObject) const
    {
    auto it = mPythonSingletonToName.find(pyObject);

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
    if (pyLineNumber == nullptr) {
        throw std::runtime_error("error getting lineNumber attr in _registerWithBlock");
        }
    if (not PyInt_Check(pyLineNumber)) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_getWithBlockLineNumber: " +
            PyObjectUtils::exc_string()
            );
       }
    lineno = PyInt_AS_LONG(pyLineNumber);
    Py_DECREF(pyLineNumber);

    return lineno;
    }



void _handleUnresolvedFreeVariableException(const PyObject* filename)
    {
    PyObject * exception, * v, * tb;

    PyErr_Fetch(&exception, &v, &tb);
    if (exception == nullptr) {
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
        if (unresolvedFreeVariableExceptionWithTrace == nullptr) {
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
        nullptr);
    }


void
PyObjectWalker::_registerStackTraceAsJson(int64_t objectId,
                                          const PyObject* pyObject) const
    {
    PyObject* pythonTraceBackAsJson = _pythonTracebackToJson(pyObject);
    if (pythonTraceBackAsJson == nullptr) {
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
    if (withBlockFun == nullptr) {
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
    if (chainsWithPositions == nullptr) {
        Py_DECREF(withBlockFun);
        throw std::runtime_error(
            "py error getting freeMemberAccessChainsWithPositions "
            "in PyObjectWalker::_registerWithBlock: "+
            PyObjectUtils::exc_string());
        }

    PyObject* boundVariables = PyObject_GetAttrString(pyObject, "boundVariables");
    if (boundVariables == nullptr) {
        Py_DECREF(chainsWithPositions);
        Py_DECREF(withBlockFun);
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerWithBlock: " +
            PyObjectUtils::exc_string()
            );
        }

    _augmentChainsWithBoundValuesInScope(
        pyObject,
        withBlockFun,
        boundVariables,
        chainsWithPositions);

    Py_DECREF(withBlockFun);
    
    PyObject* pyConvertedObjectCache = _getPyConvertedObjectCache();
    if (pyConvertedObjectCache == nullptr) {
        Py_DECREF(boundVariables);
        Py_DECREF(chainsWithPositions);
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerWithBlock: " +
            PyObjectUtils::exc_string()
            );
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
    if (filename == nullptr) {
        Py_XDECREF(resolutions);
        throw std::runtime_error(
            "py error getting sourceFileName attr "
            "in PyObjectWalker::_registerWithBlock: "
            + PyObjectUtils::exc_string()
            );
        }

    if (resolutions == nullptr) {
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
    if (boundValuesInScopeWithPositions == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* unboundLocals = PyObject_GetAttrString(pyObject, "unboundLocals");
    if (unboundLocals == nullptr) {
        Py_DECREF(boundValuesInScopeWithPositions);
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* iterator = PyObject_GetIter(boundValuesInScopeWithPositions);
    if (iterator == nullptr) {
        Py_DECREF(unboundLocals);
        Py_DECREF(boundValuesInScopeWithPositions);
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }    
    PyObject* item;
    while ((item = PyIter_Next(iterator)) != nullptr) {
        if (!PyTuple_Check(item)) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            Py_DECREF(unboundLocals);
            Py_DECREF(boundValuesInScopeWithPositions);
            throw std::runtime_error(
                "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
                PyObjectUtils::exc_string()
                );
            }
        if (PyTuple_GET_SIZE(item) != 2) {
            Py_DECREF(item);
            Py_DECREF(iterator);
            Py_DECREF(unboundLocals);
            Py_DECREF(boundValuesInScopeWithPositions);
            throw std::runtime_error(
                "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
                PyObjectUtils::exc_string()
                );
            }

        PyObject* val = PyTuple_GET_ITEM(item, 0);
        PyObject* pos = PyTuple_GET_ITEM(item, 1);

        if (not PyObjectUtils::in(unboundLocals, val) and 
                PyObjectUtils::in(boundVariables, val))
            {
            PyObject* varWithPosition = 
                PyAstFreeVariableAnalyses::varWithPosition(val, pos);
            if (varWithPosition == nullptr) {
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

        Py_DECREF(item);
        }

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
    PyObject* key;
    PyObject* value;
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
    if (__name__attr == nullptr) {
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
    if (textAndFilename == nullptr) {
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
    if (sourceAst == nullptr) {
        Py_DECREF(textAndFilename);
        throw std::runtime_error(
            "an error occured calling pyAstFromText: " + PyObjectUtils::exc_string()
            + "\nfilename = " + PyObjectUtils::str_string(filename)
            + "\ntext = " + PyObjectUtils::str_string(text)
            );
        }

    PyObject* pyAst = nullptr;
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

    if (pyAst == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_classOrFunctionInfo: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject* resolutions =
        _computeAndResolveFreeVariableMemberAccessChainsInAst(obj, pyAst);

    Py_DECREF(pyAst);

    if (resolutions == nullptr) {
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
    if (tr == nullptr) {
        return nullptr;
        }

    for (const auto& p: mConvertedObjectCache)
        {
        PyObject* pyLong = PyLong_FromLong(p.first);
        if (pyLong == nullptr) {
            Py_DECREF(tr);
            throw std::runtime_error("error getting python long from C long");
            }

        if (PyDict_SetItem(tr, pyLong, p.second) != 0) {
            return nullptr;
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
    if (chainsWithPositions == nullptr) {
        return nullptr;
        }

    PyObject* pyConvertedObjectCache = _getPyConvertedObjectCache();
    if (pyConvertedObjectCache == nullptr) {
        Py_DECREF(chainsWithPositions);
        return nullptr;
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

    if (bases == nullptr) {
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

        auto it = mPyObjectToObjectId.find(item);
        
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
    if (classObject == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerClassInstance: " +
            PyObjectUtils::exc_string()
            );
        }

    int64_t classId = walkPyObject(classObject);

    if (mObjectRegistry.isUnconvertible(classId)) {
        PyObject* modulePathOrNone = 
            mModuleLevelObjectIndex.getPathToObject(pyObject);
        if (modulePathOrNone == nullptr) {
            throw std::runtime_error(
                "py error in PyObjectWalker::_registerClassInstance: " +
                PyObjectUtils::exc_string()
                );
            }

        mObjectRegistry.defineUnconvertible(
            objectId,
            modulePathOrNone
            );

        Py_DECREF(modulePathOrNone);

        return;
        }

    PyObject* dataMemberNames = _getDataMemberNames(pyObject, classObject);
    if (dataMemberNames == nullptr) {
        Py_DECREF(classObject);
        throw std::runtime_error("py error in _registerClassInstance:" +
            PyObjectUtils::exc_string()
            );
        }

    Py_DECREF(classObject);

    if (not PyList_Check(dataMemberNames)) {
        Py_DECREF(dataMemberNames);
        throw std::runtime_error("py error in _registerClassInstance:" +
            PyObjectUtils::exc_string()
            );
        }

    std::map<std::string, int64_t> classMemberNameToClassMemberId;

    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(dataMemberNames); ++ix)
        {
        PyObject* dataMemberName = PyList_GET_ITEM(dataMemberNames, ix);
        if (not PyString_Check(dataMemberName)) {
            Py_DECREF(dataMemberName);
            Py_DECREF(dataMemberNames);
            throw std::runtime_error("py error in _registerClassInstance:" +
                PyObjectUtils::exc_string()
                );
            }

        PyObject* dataMember = PyObject_GetAttr(pyObject, dataMemberName);
        if (dataMember == nullptr) {
            Py_DECREF(dataMemberName);
            Py_DECREF(dataMemberNames);
            throw std::runtime_error("py error in _registerClassInstance:" +
                PyObjectUtils::exc_string()
                );
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
        if (__dict__attr == nullptr) {
            return nullptr;
            }
        if (not PyDict_Check(__dict__attr)) {
            Py_DECREF(__dict__attr);
            PyErr_SetString(
                PyExc_TypeError,
                "expected __dict__ attr to be a dict"
                );
            return nullptr;
            }
        PyObject* keys = PyDict_Keys(__dict__attr);
        Py_DECREF(__dict__attr);
        if (keys == nullptr) {
            return nullptr;
            }
        if (not PyList_Check(keys)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected keys to be a list"
                );
            return nullptr;
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
    if (sourceText == nullptr) {
        return nullptr;
        }

    PyObject* sourceTree = PyAstUtil::pyAstFromText(sourceText);
    Py_DECREF(sourceText);
    if (sourceTree == nullptr) {
        return nullptr;
        }

    PyObject* withBlockAst = PyAstUtil::withBlockAtLineNumber(sourceTree, lineno);
    Py_DECREF(sourceTree);
    if (withBlockAst == nullptr) {
        return nullptr;
        }

    PyObject* body = PyObject_GetAttrString(withBlockAst, "body");
    Py_DECREF(withBlockAst);
    if (body == nullptr) {
        return nullptr;
        }

    PyObject* argsTuple = Py_BuildValue("()");
    if (argsTuple == nullptr) {
        Py_DECREF(body);
        return nullptr;
        }

    PyObject* ast_args = _defaultAstArgs();
    if (ast_args == nullptr) {
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return nullptr;
        }
    
    PyObject* decorator_list = PyList_New(0);
    if (decorator_list == nullptr) {
        Py_DECREF(ast_args);
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return nullptr;
        }

    PyObject* kwds = Py_BuildValue("{s:s, s:O, s:O, s:O, s:i, s:i}",
        "name", "",
        "args", ast_args,
        "body", body,
        "decorator_list", decorator_list,
        "lineno", lineno,
        "col_offset", 0);
    if (kwds == nullptr) {
        Py_DECREF(decorator_list);
        Py_DECREF(ast_args);
        Py_DECREF(argsTuple);
        Py_DECREF(body);
        return nullptr;
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
    PyObject* args = PyTuple_New(0);
    if (args == nullptr) {
        return nullptr;
        }

    PyObject* emptyList = PyList_New(0);
    if (emptyList == nullptr) {
        Py_DECREF(args);
        return nullptr;
        }

    PyObject* kwargs = Py_BuildValue("{s:O, s:O, s:s, s:s}",
        "args", emptyList,
        "defaults", emptyList,
        "kwarg", nullptr,
        "vararg", nullptr);
    if (kwargs == nullptr) {
        Py_DECREF(emptyList);
        Py_DECREF(args);
        return nullptr;
        }
    
    PyObject* res = Ast::arguments(args, kwargs);

    Py_DECREF(kwargs);
    Py_DECREF(emptyList);
    Py_DECREF(args);

    if (res == nullptr) {
        return nullptr;
        }

    return res;
    }


void PyObjectWalker::_registerInstanceMethod(int64_t objectId, PyObject* pyObject)
    {
    PyObject* __self__attr = PyObject_GetAttrString(pyObject, "__self__");
    if (__self__attr == nullptr) {
        throw std::runtime_error(
            "expected to have a __self__ attr on instancemethods"
            );
        }

    PyObject* __name__attr = PyObject_GetAttrString(pyObject, "__name__");
    if (__name__attr == nullptr) {
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
