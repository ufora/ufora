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

#include "ClassOrFunctionInfo.hpp"
#include "FileDescription.hpp"
#include "FreeVariableResolver.hpp"
#include "PyObjectUtils.hpp"
#include "exceptions/PyforaErrors.hpp"

#include <cassert>
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
        const PyObjectPtr& purePythonClassMapping,
        BinaryObjectRegistry& objectRegistry,
        const PyObjectPtr& excludePredicateFun,
        const PyObjectPtr& excludeList,
        const PyObjectPtr& terminalValueFilter,
        const PyObjectPtr& traceback_type,
        const PyObjectPtr& pythonTracebackToJsonFun) :
            mPureImplementationMappings(purePythonClassMapping),
            mExcludePredicateFun(excludePredicateFun),
            mExcludeList(excludeList),
            mTracebackType(traceback_type),
            mPythonTracebackToJsonFun(pythonTracebackToJsonFun),
            mObjectRegistry(objectRegistry),
            mFreeVariableResolver(excludeList, terminalValueFilter)
    {
    _initPythonSingletonToName();
    _initRemotePythonObjectClass();
    _initPackedHomogenousDataClass();
    _initFutureClass();
    _initPyforaWithBlockClass();
    _initUnconvertibleClass();
    _initPyforaConnectHack();
    }


void PyObjectWalker::_initPyforaWithBlockClass()
    {
    PyObjectPtr withBlockModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.PyforaWithBlock"));
    if (withBlockModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPyforaWithBlockClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mPyforaWithBlockClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            withBlockModule.get(),
            "PyforaWithBlock"
            )
        );
    if (mPyforaWithBlockClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPyforaWithBlockClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initFutureClass()
    {
    PyObjectPtr futureModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.Future"));
    if (futureModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initFutureClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mFutureClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(futureModule.get(), "Future"));
    if (mFutureClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initFutureClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPackedHomogenousDataClass()
    {
    PyObjectPtr typeDescriptionModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.TypeDescription"));
    if (typeDescriptionModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPackedHomogenousDataClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mPackedHomogenousDataClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(typeDescriptionModule.get(),
                               "PackedHomogenousData")
        );
    if (mPackedHomogenousDataClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPackedHomogenousDataClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initRemotePythonObjectClass()
    {
    PyObjectPtr remotePythonObjectModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.RemotePythonObject"));
    if (remotePythonObjectModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initRemotePythonObjectClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mRemotePythonObjectClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(remotePythonObjectModule.get(),
                               "RemotePythonObject")
        );
    if (mRemotePythonObjectClass == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initRemotePythonObjectClass: " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPythonSingletonToName()
    {
    PyObjectPtr namedSingletonsModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.NamedSingletons"));
    if (namedSingletonsModule == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr pythonSingletonToName = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            namedSingletonsModule.get(),
            "pythonSingletonToName"
            )
        );
    if (pythonSingletonToName == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyDict_Check(pythonSingletonToName.get())) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_initPythonSingletonToName: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObject * key, * value;
    Py_ssize_t pos = 0;
    char* string = nullptr;
    Py_ssize_t length = 0;

    while (PyDict_Next(pythonSingletonToName.get(), &pos, &key, &value)) {
        if (PyString_AsStringAndSize(value, &string, &length) == -1) {
            throw std::runtime_error(
                "py err in PyObjectWalker::_initPythonSingletonToName: " +
                PyObjectUtils::exc_string()
                );
            }

        Py_INCREF(key);
        mPythonSingletonToName[key] = std::string(string, length);
        }
    }


void PyObjectWalker::_initUnconvertibleClass() {
    PyObjectPtr unconvertibleModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.Unconvertible"));
    if (unconvertibleModule == nullptr) {
        throw std::runtime_error(
            "py error getting unconvertibleModule in "
            "PyObjectWalker::_initUnconvertibleClass: " +
            PyObjectUtils::exc_string()
            );
        }

    mUnconvertibleClass = PyObjectPtr::unincremented(PyObject_GetAttrString(
            unconvertibleModule.get(),
            "Unconvertible"
            ));

    if (mUnconvertibleClass == nullptr) {
        throw std::runtime_error(
            "py error getting unconvertibleModule in "
            "PyObjectWalker::_initUnconvertibleClass " +
            PyObjectUtils::exc_string()
            );
        }
    }


void PyObjectWalker::_initPyforaConnectHack() {
    PyObjectPtr pyforaModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora"));
    if (pyforaModule == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker::_initPyforaConnectHack: " +
            PyObjectUtils::exc_string()
            );
        }

    mPyforaConnectHack = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyforaModule.get(), "connect"));
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
    for (const auto& p: mPyObjectToObjectId) {
        Py_DECREF(p.first);
        }

    for (const auto& p: mPythonSingletonToName) {
        Py_DECREF(p.first);
        }
    }


int64_t PyObjectWalker::_allocateId(PyObject* pyObject) {
    int64_t objectId = mObjectRegistry.allocateObject();

    Py_INCREF(pyObject);
    mPyObjectToObjectId[pyObject] = objectId;

    return objectId;
    }


PyObjectWalker::WalkResult PyObjectWalker::walkPyObject(PyObject* pyObject) 
    {
    WalkResult tr;

        {
        auto it = mPyObjectToObjectId.find(pyObject);

        if (it != mPyObjectToObjectId.end()) {
            tr.set<int64_t>(it->second);
            return tr;
            }
        }
    
        {
        auto it = mConvertedObjectCache.find(
            PyObjectUtils::builtin_id(pyObject)
            );

        if (it != mConvertedObjectCache.end()) {
            pyObject = it->second.get();
            }
        }

    bool wasReplaced = false;
    if (mPureImplementationMappings.canMap(pyObject)) {
        pyObject = _pureInstanceReplacement(pyObject);

        assert (pyObject != nullptr);

        wasReplaced = true;
        }

    int64_t objectId = _allocateId(pyObject);

    if (pyObject == mPyforaConnectHack.get()) {
        _registerUnconvertible(objectId, Py_None);
        tr.set<int64_t>(objectId);
        return tr;
        }
    
    PyforaErrorOrNull res = _walkPyObject(pyObject, objectId);

    if (res) {
        _registerUnconvertible(objectId, pyObject);
        }

    if (wasReplaced) {
        Py_DECREF(pyObject);
        }

    tr.set<int64_t>(objectId);
    return tr;
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


namespace {
std::string _rootNameOfVarWithPosition(PyObject* varWithPosition)
    {
    //VarWithPosition(var=('x',), pos=PositionInFile(lineno=519, col_offset=19))
    PyObjectPtr varMember = PyObjectPtr::unincremented(
        PyObject_GetAttrString(varWithPosition, "var"));
    if (varMember == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "getting var member: " +
            PyObjectUtils::format_exc()
            );
        }

    if (not PyTuple_Check(varMember.get())) {
        throw std::runtime_error(
            "PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "expects var member to be a tuple"
            );
        }
    if (PyTuple_GET_SIZE(varMember.get()) == 0) {
        throw std::runtime_error(
            "PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "expects its var member tuple to have length at least one"
            );
        }
    
    // borrowed reference
    PyObject* rootName = PyTuple_GET_ITEM(varMember.get(), 0);
    if (not PyString_Check(rootName)) {
        throw std::runtime_error(
            "PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition expects "
            "its var member tuple to contain strings"
            );
        }

    return std::string(PyString_AS_STRING(rootName),
                       PyString_GET_SIZE(rootName));
    }


std::pair<int64_t, int64_t> _lineAndColumn(PyObject* varWithPosition)
    {
    //VarWithPosition(var=('x',), pos=PositionInFile(lineno=519, col_offset=19))
    PyObjectPtr posMember = PyObjectPtr::unincremented(
        PyObject_GetAttrString(varWithPosition, "pos"));
    if (posMember == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "getting pos member: " + PyObjectUtils::format_exc()
            );
        }

    PyObjectPtr lineno = PyObjectPtr::unincremented(
        PyObject_GetAttrString(posMember.get(), "lineno")
        );
    PyObjectPtr col_offset = PyObjectPtr::unincremented(
        PyObject_GetAttrString(posMember.get(), "col_offset")
        );

    if (lineno == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "getting lineno member: " + PyObjectUtils::format_exc()
            );        
        }
    if (col_offset == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition "
            "getting col_offset member: " + PyObjectUtils::format_exc()
            );        
        }

    if (not PyInt_Check(lineno.get())) {
        throw std::runtime_error(
            "PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition expects "
            "lineno to be an int"
            );
        }
    if (not PyInt_Check(col_offset.get())) {
        throw std::runtime_error(
            "PyObjectWalker::<anonymous>::_rootNameOfVarWithPosition expects "
            "col_offset to be an int"
            );
        }

    int64_t linenoCpp = PyInt_AS_LONG(lineno.get());
    int64_t col_offset_cpp = PyInt_AS_LONG(col_offset.get());

    return std::make_pair(linenoCpp, col_offset_cpp);
    }
}

int64_t PyObjectWalker::walkUnresolvedVarWithPosition(PyObject* varWithPosition)
    {
    //VarWithPosition(var=('x',), pos=PositionInFile(lineno=519, col_offset=19))

    std::string rootNameCpp = _rootNameOfVarWithPosition(varWithPosition);
    std::pair<int64_t, int64_t> lineAndCol = _lineAndColumn(varWithPosition);

    int64_t objectId = mObjectRegistry.allocateObject();

    mObjectRegistry.defineUnresolvedVarWithPosition(
        objectId,
        rootNameCpp,
        lineAndCol.first,
        lineAndCol.second);
    
    return objectId;
    }


PyObject* PyObjectWalker::_pureInstanceReplacement(const PyObject* pyObject)
    {
    PyObject* pureInstance = mPureImplementationMappings.mappableInstanceToPure(
        pyObject);
    if (pureInstance == nullptr) {
        return nullptr;
        }

    mConvertedObjectCache[PyObjectUtils::builtin_id(pyObject)] =
        PyObjectPtr::unincremented(pureInstance);

    return pureInstance;
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_walkPyObject(PyObject* pyObject, int64_t objectId) {
    if (PyObject_IsInstance(pyObject, mRemotePythonObjectClass.get()))
        {
        return _registerRemotePythonObject(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mPackedHomogenousDataClass.get()))
        {
        return _registerPackedHomogenousData(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mFutureClass.get()))
        {
        return _registerFuture(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, PyExc_Exception)
            and _classIsNamedSingleton(pyObject))
        {
        return _registerBuiltinExceptionInstance(objectId, pyObject);
        }
    else if (_isTypeOrBuiltinFunctionAndInNamedSingletons(pyObject))
        {
        return _registerTypeOrBuiltinFunctionNamedSingleton(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mTracebackType.get()))
        {
        return _registerStackTraceAsJson(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mPyforaWithBlockClass.get()))
        {
        return _registerPyforaWithBlock(objectId, pyObject);
        }
    else if (PyObject_IsInstance(pyObject, mUnconvertibleClass.get()))
        {
        PyObjectPtr objectThatsNotConvertible = PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                pyObject,
                "objectThatsNotConvertible"
                ));
        if (objectThatsNotConvertible == nullptr) {
            throw std::runtime_error(
                "expected Unconvertible instances to have an "
                "`objectThatsNotConvertible` member"
                );
            }

        return _registerUnconvertible(objectId, objectThatsNotConvertible.get());
        }
    else if (PyTuple_Check(pyObject))
        {
        return _registerTuple(objectId, pyObject);
        }
    else if (PyList_Check(pyObject))
        {
        return _registerList(objectId, pyObject);
        }
    else if (PyDict_Check(pyObject))
        {
        return _registerDict(objectId, pyObject);
        }
    else if (_isPrimitive(pyObject))
        {
        _registerPrimitive(objectId, pyObject);
        return {};
        }
    else if (PyFunction_Check(pyObject))
        {
        return _registerFunction(objectId, pyObject);
        }
    else if (mPyforaInspectModule.isclass(pyObject))
        {
        return _registerClass(objectId, pyObject);
        }
    else if (PyMethod_Check(pyObject))
        {
        return _registerInstanceMethod(objectId, pyObject);
        }
    else if (mPyforaInspectModule.isclassinstance(pyObject))
        {
        return _registerClassInstance(objectId, pyObject);
        }
    else {
        throw std::runtime_error("PyObjectWalker couldn't handle a PyObject: " +
            PyObjectUtils::repr_string(pyObject));
        }
    }


bool PyObjectWalker::_classIsNamedSingleton(PyObject* pyObject) const
    {
    PyObjectPtr __class__attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "__class__"));

    if (__class__attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_classIsNamedSingleton: " +
            PyObjectUtils::exc_string()
            );
        }

    bool tr = (mPythonSingletonToName.find(__class__attr.get()) != 
        mPythonSingletonToName.end());

    return tr;
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerRemotePythonObject(int64_t objectId,
                                            PyObject* pyObject) const
    {
    PyObjectPtr _pyforaComputedValueArg_attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObject,
            "_pyforaComputedValueArg"
            ));
    if (_pyforaComputedValueArg_attr == nullptr) {
        throw std::runtime_error(
            "py error getting _pyforaComputedValueArg "
            "in PyObjectWalker::_registerRemotePythonObject: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(
            _pyforaComputedValueArg_attr.get(),
            nullptr
            ));
    
    if (res == nullptr) {
        throw std::runtime_error(
            "py error calling _pyforaComputedValueArg "
            "in PyObjectWalker::_registerRemotePythonObject: " +
            PyObjectUtils::exc_string()
            );
        }

    mObjectRegistry.defineRemotePythonObject(
        objectId,
        res.get()
        );
    return {};
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerUnconvertible(int64_t objectId,
                                            const PyObject* pyObject) const
    {
    PyObjectPtr modulePathOrNone = PyObjectPtr::unincremented(
        mModuleLevelObjectIndex.getPathToObject(pyObject));
    if (modulePathOrNone == nullptr) {
        throw std::runtime_error("error getting modulePathOrNone"
            "in PyObjectWalker::_registerUnconvertible");
        }

    mObjectRegistry.defineUnconvertible(objectId, modulePathOrNone.get());

    return {};
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerPackedHomogenousData(int64_t objectId,
                                                                PyObject* pyObject) const
    {
    mObjectRegistry.definePackedHomogenousData(objectId, pyObject);
    return {};
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerFuture(int64_t objectId, PyObject* pyObject)
    {
    PyObjectPtr result_attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "result"));
    if (result_attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerFuture: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr res = PyObjectPtr::unincremented(
        PyObject_CallFunctionObjArgs(result_attr.get(), nullptr));
    if (res == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerFuture: " +
            PyObjectUtils::exc_string()
            );
        }

    return _walkPyObject(res.get(), objectId);
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerBuiltinExceptionInstance(
        int64_t objectId,
        PyObject* pyException)
    {
    PyObjectPtr __class__attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyException, "__class__"));
    if (__class__attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerBuiltinExceptionInstance: " +
            PyObjectUtils::exc_string()
            );
        }

    auto it = mPythonSingletonToName.find(__class__attr.get());
    if (it == mPythonSingletonToName.end()) {
        throw std::runtime_error(
            "it's supposed to be a precondition to this function that this not happen");
        }

    PyObjectPtr args_attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyException, "args"));
    if (args_attr == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerBuiltinExceptionInstance: " +
            PyObjectUtils::exc_string()
            );
        }

    WalkResult argsIdOrErr = walkPyObject(args_attr.get());

    if (argsIdOrErr.is<int64_t>()) {
        mObjectRegistry.defineBuiltinExceptionInstance(objectId,
                                                       it->second,
                                                       argsIdOrErr.get<int64_t>());
        return {};
        }
    else {
        return argsIdOrErr.get<std::shared_ptr<PyforaError>>();
        }
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
    PyObjectPtr lines = PyObjectPtr::unincremented(
        mPyforaInspectModule.getlines(fileNamePyObj));
    if (lines == nullptr) {
        throw std::runtime_error(
            "error calling getlines");
        }
    
    if (not PyList_Check(lines.get())) {
        throw std::runtime_error("expected a list");
        }

    std::ostringstream oss;
    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(lines.get()); ++ix)
        {
        // borrowed reference. no need to decref
        PyObject* item = PyList_GET_ITEM(lines.get(), ix);
        
        if (PyString_Check(item)) {
            oss.write(PyString_AS_STRING(item), PyString_GET_SIZE(item));
            }
        else if (PyUnicode_Check(item)) {
            PyObjectPtr pyString = PyObjectPtr::unincremented(
                PyUnicode_AsASCIIString(item));
            if (pyString == nullptr) {
                throw std::runtime_error("error getting string from unicode: " + 
                    PyObjectUtils::exc_string());
                }

            oss.write(PyString_AS_STRING(pyString.get()),
                      PyString_GET_SIZE(pyString.get()));
            }
        else {
            throw std::runtime_error(
                "all elements in lines should be str or unicode");
            }

        }
    
    return oss.str();
    }


std::string PyObjectWalker::_fileText(const std::string& filename) const
    {
    PyObjectPtr fileNamePyObj = PyObjectPtr::unincremented(
        PyString_FromStringAndSize(
            filename.data(),
            filename.size()));
    if (fileNamePyObj == nullptr) {
        throw std::runtime_error("couldn't create a python string out of a std::string");
        }

    std::string tr =  _fileText(fileNamePyObj.get());

    return tr;
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerTypeOrBuiltinFunctionNamedSingleton(
        int64_t objectId,
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
    return {};
    }


namespace {

int64_t _getWithBlockLineNumber(PyObject* withBlock)
    {
    int64_t lineno;
    PyObjectPtr pyLineNumber = PyObjectPtr::unincremented(
        PyObject_GetAttrString(withBlock, "lineNumber"));
    if (pyLineNumber == nullptr) {
        throw std::runtime_error("error getting lineNumber attr in _registerPyforaWithBlock");
        }
    if (not PyInt_Check(pyLineNumber.get())) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_getWithBlockLineNumber: " +
            PyObjectUtils::exc_string()
            );
       }
    lineno = PyInt_AS_LONG(pyLineNumber.get());

    return lineno;
    }



}


std::shared_ptr<PyforaError> PyObjectWalker::_handleUnresolvedFreeVariableException(
        const PyObject* filename)
    {
    PyObject * exception, * v, * tb;

    PyErr_Fetch(&exception, &v, &tb);
    if (exception == nullptr) {
        throw std::runtime_error("expected an Exception to be set.");
        }

    PyErr_NormalizeException(&exception, &v, &tb);

    if (PyObject_IsInstance(
            v,
            mUnresolvedFreeVariableExceptions.getUnresolvedFreeVariableExceptionClass()))
        {
        // borrowed reference.
        PyObject* unresolvedFreeVariableExceptionWithTrace =
            mUnresolvedFreeVariableExceptions.getUnresolvedFreeVariableExceptionWithTrace(
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
            PyObjectPtr::unincremented(unresolvedFreeVariableExceptionWithTrace)
            );
        }
    else {
        PyErr_Restore(exception, v, tb);
        throw std::runtime_error(
            "PyObjectWalker::<anonymous namespace>::"
            "_handleUnresolvedFreeVariableException: " +
            PyObjectUtils::format_exc());
        }
    }


PyObject* PyObjectWalker::_pythonTracebackToJson(const PyObject* pyObject) const
    {
    return PyObject_CallFunctionObjArgs(
        mPythonTracebackToJsonFun.get(),
        pyObject,
        nullptr);
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerStackTraceAsJson(int64_t objectId,
                                          const PyObject* pyObject) const
    {
    PyObjectPtr pythonTraceBackAsJson = PyObjectPtr::unincremented(
        _pythonTracebackToJson(pyObject));
    if (pythonTraceBackAsJson == nullptr) {
        throw std::runtime_error(
            "py error in PyObjectWalker:_registerStackTraceAsJson: " +
            PyObjectUtils::exc_string()
            );
        }

    mObjectRegistry.defineStacktrace(objectId, pythonTraceBackAsJson.get());
    return {};
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerPyforaWithBlock(
        int64_t objectId,
        PyObject* pyObject)
    {
    int64_t lineno = _getWithBlockLineNumber(pyObject);

    PyObjectPtr withBlockFun = PyObjectPtr::unincremented(
        _withBlockFun(pyObject, lineno));
    if (withBlockFun == nullptr) {
        throw std::runtime_error(
            "error getting with block ast functionDef"
            " in PyObjectWalker::_registerPyforaWithBlock: " +
            PyObjectUtils::exc_string());
        }
    if (mPyAstUtilModule.hasReturnInOuterScope(withBlockFun.get())) {
        std::ostringstream err_oss;
        err_oss << "return statement not supported in pyfora with-block (line ";
        err_oss << mPyAstUtilModule.getReturnLocationsInOuterScope(withBlockFun.get());
        err_oss << ")";

        throw BadWithBlockError(err_oss.str());
        }
    if (mPyAstUtilModule.hasYieldInOuterScope(withBlockFun.get())) {
        std::ostringstream err_oss;
        err_oss << "yield expression not supported in pyfora with-block (line ";
        err_oss << mPyAstUtilModule.getYieldLocationsInOuterScope(withBlockFun.get());
        err_oss << ")";

        throw BadWithBlockError(err_oss.str());
        }

    PyObjectPtr chainsWithPositions = PyObjectPtr::unincremented(
        _freeMemberAccessChainsWithPositions(withBlockFun.get()));
    if (chainsWithPositions == nullptr) {
        throw std::runtime_error(
            "py error getting freeMemberAccessChainsWithPositions "
            "in PyObjectWalker::_registerPyforaWithBlock: "+
            PyObjectUtils::exc_string());
        }

    PyObjectPtr boundVariables = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "boundVariables"));
    if (boundVariables == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerPyforaWithBlock: " +
            PyObjectUtils::exc_string()
            );
        }

    _augmentChainsWithBoundValuesInScope(
        pyObject,
        withBlockFun.get(),
        boundVariables.get(),
        chainsWithPositions.get());

    PyObject* pyConvertedObjectCache = _getPyConvertedObjectCache();
    if (pyConvertedObjectCache == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerPyforaWithBlock: " +
            PyObjectUtils::exc_string()
            );
        }

    ResolutionResult resolutions =
        mFreeVariableResolver.resolveFreeVariableMemberAccessChains(
            chainsWithPositions.get(),
            boundVariables.get(),
            pyConvertedObjectCache);

    PyObjectPtr filename = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "sourceFileName"));
    if (filename == nullptr) {
        throw std::runtime_error(
            "py error getting sourceFileName attr "
            "in PyObjectWalker::_registerPyforaWithBlock: "
            + PyObjectUtils::exc_string()
            );
        }

    variant<
        std::map<FreeVariableMemberAccessChain, int64_t>,
        std::shared_ptr<PyforaError>> processedResolutionsOrErr =
            _processFreeVariableMemberAccessChainResolutions(
                resolutions
                );

    int64_t sourceFileId = walkFileDescription(
        FileDescription::cachedFromArgs(
            PyObjectUtils::std_string(filename.get()),
            _fileText(filename.get())
            )
        );

    if (processedResolutionsOrErr.is<std::map<FreeVariableMemberAccessChain, int64_t>>())
        {
        mObjectRegistry.defineWithBlock(
            objectId,
            processedResolutionsOrErr.get<
                std::map<FreeVariableMemberAccessChain, int64_t>>(),
            sourceFileId,
            lineno);

        return {};
        }
    else {
        return processedResolutionsOrErr.get<std::shared_ptr<PyforaError>>();
        }
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
    
    PyObjectPtr boundValuesInScopeWithPositions = PyObjectPtr::unincremented(
        mPyAstFreeVariableAnalysesModule.collectBoundValuesInScope(withBlockFun, true));
    if (boundValuesInScopeWithPositions == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr unboundLocals = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "unboundLocals"));
    if (unboundLocals == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr iterator = PyObjectPtr::unincremented(
        PyObject_GetIter(boundValuesInScopeWithPositions.get()));
    if (iterator == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
            PyObjectUtils::exc_string()
            );
        }    
    PyObjectPtr item;
    while ((item = PyObjectPtr::unincremented(PyIter_Next(iterator.get())))) {
        if (!PyTuple_Check(item.get())) {
            throw std::runtime_error(
                "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
                PyObjectUtils::exc_string()
                );
            }
        if (PyTuple_GET_SIZE(item.get()) != 2) {
            throw std::runtime_error(
                "py err in PyObjectWalker::_augmentChainsWithBoundValuesInScope: " +
                PyObjectUtils::exc_string()
                );
            }

        PyObject* val = PyTuple_GET_ITEM(item.get(), 0);
        PyObject* pos = PyTuple_GET_ITEM(item.get(), 1);

        if (not PyObjectUtils::in(unboundLocals.get(), val) and 
            PyObjectUtils::in(boundVariables, val))
            {
            PyObjectPtr varWithPosition = PyObjectPtr::unincremented(
                mPyAstFreeVariableAnalysesModule.varWithPosition(val, pos));
            if (varWithPosition == nullptr) {
                throw std::runtime_error("couldn't get VarWithPosition");
                }
            if (PySet_Add(chainsWithPositions, varWithPosition.get()) != 0) {
                throw std::runtime_error("error adding to a set");
                }
            }
        }
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerTuple(int64_t objectId, PyObject* pyTuple)
    {
    std::vector<int64_t> memberIds;
    Py_ssize_t size = PyTuple_GET_SIZE(pyTuple);
    for (Py_ssize_t ix = 0; ix < size; ++ix)
        {
        WalkResult res = walkPyObject(PyTuple_GET_ITEM(pyTuple, ix));

        if (res.is<int64_t>()) {
            memberIds.push_back(
                res.get<int64_t>()
                );
            }
        else {
            return res.get<std::shared_ptr<PyforaError>>(); 
            }
        }

    mObjectRegistry.defineTuple(objectId, memberIds);
    return {};
    }
    

PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerList(int64_t objectId, PyObject* pyList)
    {
    if (_allPrimitives(pyList))
        {
        return _registerListOfPrimitives(objectId, pyList);
        }
    else {
        return _registerListGeneric(objectId, pyList);
        }
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerListOfPrimitives(int64_t objectId, PyObject* pyList) const
    {
    mObjectRegistry.definePrimitive(objectId, pyList);
    return {};
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerListGeneric(int64_t objectId, const PyObject* pyList)
    {
    std::vector<int64_t> memberIds;
    Py_ssize_t size = PyList_GET_SIZE(pyList);
    for (Py_ssize_t ix = 0; ix < size; ++ix)
        {
        WalkResult res = walkPyObject(PyList_GET_ITEM(pyList, ix));

        if (res.is<int64_t>()) {
            memberIds.push_back(
                res.get<int64_t>()
                );
            }
        else {
            return res.get<std::shared_ptr<PyforaError>>(); 
            }
        }

    mObjectRegistry.defineList(objectId, memberIds);
    return {};
    }
    

PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerDict(int64_t objectId, PyObject* pyDict)
    {
    std::vector<int64_t> keyIds;
    std::vector<int64_t> valueIds;
    PyObject* key;
    PyObject* value;
    Py_ssize_t pos = 0;
    
    while (PyDict_Next(pyDict, &pos, &key, &value)) {
        WalkResult res = walkPyObject(key);

        if (res.is<int64_t>()) {
            keyIds.push_back(
                res.get<int64_t>()
                );
            }
        else {
            return res.get<std::shared_ptr<PyforaError>>(); 
            }

        res = walkPyObject(value);

        if (res.is<int64_t>()) {
            valueIds.push_back(
                res.get<int64_t>()
                );
            }
        else {
            return res.get<std::shared_ptr<PyforaError>>(); 
            }
        }

    mObjectRegistry.defineDict(objectId, keyIds, valueIds);
    return {};
    }
    

PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerFunction(int64_t objectId, PyObject* pyObject)
    {
    auto infoOrException = _classOrFunctionInfo(pyObject, true);
    if (infoOrException.is<ClassOrFunctionInfo>()) {
        ClassOrFunctionInfo info = infoOrException.get<ClassOrFunctionInfo>();
        mObjectRegistry.defineFunction(
            objectId,
            info.sourceFileId(),
            info.lineNumber(),
            info.freeVariableMemberAccessChainsToId()
            );
        return {};
        }
    else {
        return infoOrException.get<std::shared_ptr<PyforaError>>();
        }
    }


namespace {

// precondition: obj should be a function or class
void _checkForInlineForaName(PyObject* obj) {
    PyObjectPtr __name__attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(obj, "__name__"));
    if (__name__attr == nullptr) {
        throw std::runtime_error(
            "expected to find a __name__attr "
            "in PyObjectWalker::<anonymous namespace>::"
            "_checkForInlineForaName: " +
            PyObjectUtils::exc_string()
            );
        }
    if (not PyString_Check(__name__attr.get())) {
        throw std::runtime_error(
            "expected __name__ attr to be a string"
            );
        }
    
    std::string __name__attr_as_string = std::string(
        PyString_AS_STRING(__name__attr.get()),
        PyString_GET_SIZE(__name__attr.get())
        );

    if (__name__attr_as_string == "__inline_fora") {
        throw PythonToForaConversionError("in pfora, `__inline_fora` is a reserved word");
        }
    }

}


variant<ClassOrFunctionInfo, std::shared_ptr<PyforaError>>
PyObjectWalker::_classOrFunctionInfo(PyObject* obj, bool isFunction)
    {
    variant<ClassOrFunctionInfo, std::shared_ptr<PyforaError>> tr;

    // old PyObjectWalker checks for __inline_fora here
    _checkForInlineForaName(obj);

    variant<PyObjectPtr, std::shared_ptr<PyforaError>> textAndFilenameOrErr =
        mPyAstUtilModule.sourceFilenameAndText(obj);

    PyObjectPtr textAndFilename;
    if (textAndFilenameOrErr.is<PyObjectPtr>()) {
        textAndFilename = textAndFilenameOrErr.get<PyObjectPtr>();
        }
    else {
        tr.set<std::shared_ptr<PyforaError>>(
            textAndFilenameOrErr.get<std::shared_ptr<PyforaError>>()
            );
        return tr;
        }

    assert (textAndFilenameOrErr != nullptr);

    if (textAndFilename == nullptr) {
        throw std::runtime_error(
            "error calling sourceFilenameAndText: " + PyObjectUtils::exc_string()
            );
        }
    if (not PyTuple_Check(textAndFilename.get())) {
        throw std::runtime_error("expected sourceFilenameAndText to return a tuple");
        }
    if (PyTuple_GET_SIZE(textAndFilename.get()) != 2) {
        throw std::runtime_error(
            "expected sourceFilenameAndText to return a tuple of length 2"
            );
        }
    
    // borrowed reference
    PyObject* text = PyTuple_GET_ITEM(textAndFilename.get(), 0);
    // borrowed reference
    PyObject* filename = PyTuple_GET_ITEM(textAndFilename.get(), 1);

    variant<long, std::shared_ptr<PyforaError>> startingSourceLineOrErr =
        mPyAstUtilModule.startingSourceLine(obj);
    long startingSourceLine;
    
    if (startingSourceLineOrErr.is<long>()) {
        startingSourceLine = startingSourceLineOrErr.get<long>();
        }
    else {
        tr.set<std::shared_ptr<PyforaError>>(
            startingSourceLineOrErr.get<std::shared_ptr<PyforaError>>()
            );
        return tr;
        }

    PyObjectPtr sourceAst = PyObjectPtr::unincremented(
        mPyAstUtilModule.pyAstFromText(text));
    if (sourceAst == nullptr) {
        throw std::runtime_error(
            "an error occured calling pyAstFromText: " + PyObjectUtils::exc_string()
            + "\nfilename = " + PyObjectUtils::str_string(filename)
            + "\ntext = " + PyObjectUtils::str_string(text)
            );
        }

    PyObjectPtr pyAst;
    if (isFunction) {
        pyAst = PyObjectPtr::unincremented(
            mPyAstUtilModule.functionDefOrLambdaAtLineNumber(
                sourceAst.get(),
                startingSourceLine));
        }
    else {
        pyAst = PyObjectPtr::unincremented(
            mPyAstUtilModule.classDefAtLineNumber(sourceAst.get(),
                                                  startingSourceLine));
        }

    if (pyAst == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_classOrFunctionInfo: " +
            PyObjectUtils::exc_string()
            );
        }

    variant<ResolutionResult, std::shared_ptr<PyforaError>> resolutionsOrErr =
        _computeAndResolveFreeVariableMemberAccessChainsInAst(obj, pyAst.get());

    if (resolutionsOrErr.is<std::shared_ptr<PyforaError>>()) {
        tr.set<std::shared_ptr<PyforaError>>(
            resolutionsOrErr.get<std::shared_ptr<PyforaError>>()
            );
        return tr;
        }

    ResolutionResult resolutions = resolutionsOrErr.get<ResolutionResult>();

    variant<
        std::map<FreeVariableMemberAccessChain, int64_t>,
        std::shared_ptr<PyforaError>> processedResolutionsOrErr =
            _processFreeVariableMemberAccessChainResolutions(
                resolutions
                );

    if (processedResolutionsOrErr.is<std::map<FreeVariableMemberAccessChain, int64_t>>())
        {
        int64_t fileId = walkFileDescription(
            FileDescription::cachedFromArgs(
                PyObjectUtils::std_string(filename),
                PyObjectUtils::std_string(text)
                )
            );

        // can we setup perfect forwarding for variant?
        tr.set<ClassOrFunctionInfo>(
            ClassOrFunctionInfo(
                fileId,
                startingSourceLine,
                processedResolutionsOrErr.get<
                    std::map<FreeVariableMemberAccessChain, int64_t>
                    >()
                )
            );
        return tr;
        }
    else {
        tr.set<std::shared_ptr<PyforaError>>(
            processedResolutionsOrErr.get<std::shared_ptr<PyforaError>>()
            );
        return tr;
        }
    }


variant<std::map<FreeVariableMemberAccessChain, int64_t>,
        std::shared_ptr<PyforaError>>
PyObjectWalker::_processFreeVariableMemberAccessChainResolutions(
        const ResolutionResult& resolutions
        )
    {
    variant<std::map<FreeVariableMemberAccessChain, int64_t>,
            std::shared_ptr<PyforaError>> tr;

    std::map<FreeVariableMemberAccessChain, int64_t> cppResolutions;

    PyObject* resolvedChainsDict = resolutions.resolvedChainsDict.get();
    auto res = _processResolvedChainsDict(resolvedChainsDict, cppResolutions);

    if (res) {
        tr.set<std::shared_ptr<PyforaError>>(*res);
        return tr;
        }

    PyObject* unresolvedChainsSet = resolutions.unresolvedChainsSet.get();
    res = _processUnresolvedChainsSet(unresolvedChainsSet, cppResolutions);

    if (res) {
        tr.set<std::shared_ptr<PyforaError>>(*res);
        return tr;
        }

    tr.set<std::map<FreeVariableMemberAccessChain, int64_t>>(cppResolutions);
    return tr;
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_processResolvedChainsDict(
        PyObject* resolvedChainsDict,
        std::map<FreeVariableMemberAccessChain, int64_t>& ioResolutions
        )
    {
    if (not PyDict_Check(resolvedChainsDict)) {
        throw std::runtime_error(
            "PyObjectWalker::_processResolvedChainsDict expects a dict argument"
            );
        }

    PyObject * key, * value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(resolvedChainsDict, &pos, &key, &value)) {
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
        
        auto resolutionIdOrErr = walkPyObject(resolution);
        
        if (resolutionIdOrErr.is<std::shared_ptr<PyforaError>>()) {
            return resolutionIdOrErr.get<std::shared_ptr<PyforaError>>();
            }

        ioResolutions[toChain(key)] = resolutionIdOrErr.get<int64_t>();
        }

    return {};
    }


PyObjectWalker::PyforaErrorOrNull PyObjectWalker::_processUnresolvedChainsSet(
        PyObject* unresolvedChainsSet,
        std::map<FreeVariableMemberAccessChain, int64_t>& ioResolutions
        )
    {
    if (not PySet_Check(unresolvedChainsSet)) {
        throw std::runtime_error(
            "PyObjectWalker::_processResolvedChainsSet expects a set argument"
            );
        }

    PyObjectPtr iterator = PyObjectPtr::unincremented(
        PyObject_GetIter(unresolvedChainsSet));
    if (iterator == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_processResolvedChainsSet: " +
            PyObjectUtils::exc_string()
            );
        }

    PyObjectPtr item;
    while ((item = PyObjectPtr::unincremented(PyIter_Next(iterator.get())))) {
        int64_t objectId = walkUnresolvedVarWithPosition(item.get());

        PyObjectPtr pyChain = PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                item.get(),
                "var"
                )
            );
        if (pyChain == nullptr) {
            throw std::runtime_error(
                "PyObjectWalker::_processResolvedChainsSet py error: " +
                PyObjectUtils::format_exc()
                );
            }

        ioResolutions[toChain(pyChain.get())] = objectId;
        }

    return {};
    }


PyObject* PyObjectWalker::_getPyConvertedObjectCache() const
    {
    PyObject* tr = PyDict_New();
    if (tr == nullptr) {
        return nullptr;
        }

    for (const auto& p: mConvertedObjectCache)
        {
        PyObjectPtr pyLong = PyObjectPtr::unincremented(PyLong_FromLong(p.first));
        if (pyLong == nullptr) {
            Py_DECREF(tr);
            throw std::runtime_error("error getting python long from C long");
            }

        if (PyDict_SetItem(tr, pyLong.get(), p.second.get()) != 0) {
            return nullptr;
            }
        }

    return tr;
    }


variant<ResolutionResult, std::shared_ptr<PyforaError>>
PyObjectWalker::_computeAndResolveFreeVariableMemberAccessChainsInAst(
        const PyObject* pyObject,
        const PyObject* pyAst
        ) const
    {
    variant<ResolutionResult, std::shared_ptr<PyforaError>> tr;

    PyObjectPtr chainsWithPositions = PyObjectPtr::unincremented(
        _freeMemberAccessChainsWithPositions(pyAst));
    if (chainsWithPositions == nullptr) {
        tr.set<std::shared_ptr<PyforaError>>(
            std::shared_ptr<PyforaError>(
                new PyforaError(
                    "py error getting free member access chains in PyObjectWalker::"
                    "_computeAndResolveFreeVariableMemberAccessChainsInAst: " +
                    PyObjectUtils::format_exc()
                    )
                )
            );
        return tr;
        }

    PyObjectPtr pyConvertedObjectCache = PyObjectPtr::unincremented(
        _getPyConvertedObjectCache());
    if (pyConvertedObjectCache == nullptr) {
        throw std::runtime_error(
            "py error getting converted object cache in PyObjectWalker::"
            "_computeAndResolveFreeVariableMemberAccessChainsInAst: " +
            PyObjectUtils::format_exc()
            );
        }

    tr.set<ResolutionResult>(
        mFreeVariableResolver.resolveFreeVariableMemberAccessChainsInAst(
            pyObject,
            pyAst,
            chainsWithPositions.get(),
            pyConvertedObjectCache.get()
            )
        );

    return tr;
    }


PyObject* PyObjectWalker::_freeMemberAccessChainsWithPositions(
        const PyObject* pyAst
        ) const
    {
    return mPyAstFreeVariableAnalysesModule.getFreeMemberAccessChainsWithPositions(
            pyAst,
            false,
            true,
            mExcludePredicateFun.get()
            );
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerClass(int64_t objectId, PyObject* pyObject)
    {
    auto infoOrException = _classOrFunctionInfo(pyObject, false);
    if (infoOrException.is<ClassOrFunctionInfo>()) {
        ClassOrFunctionInfo info = infoOrException.get<ClassOrFunctionInfo>();
        PyObjectPtr bases = PyObjectPtr::unincremented(
            PyObject_GetAttrString(
                pyObject,
                "__bases__"));

        if (bases == nullptr) {
            throw std::runtime_error(
                "couldn't get __bases__ member of an object we expected to be a class"
                );
            }
        if (not PyTuple_Check(bases.get())) {
            throw std::runtime_error("expected bases to be a list");
            }

        std::vector<int64_t> baseClassIds;
        for (Py_ssize_t ix = 0; ix < PyTuple_GET_SIZE(bases.get()); ++ix)
            {
            PyObject* item = PyTuple_GET_ITEM(bases.get(), ix);

            auto it = mPyObjectToObjectId.find(item);
        
            if (it == mPyObjectToObjectId.end()) {
                return std::shared_ptr<PyforaError>(
                    new PyforaError(
                        "expected each base class to have a registered id"
                        ". class = " + PyObjectUtils::str_string(pyObject)
                        )
                    );
                }
        
            baseClassIds.push_back(it->second);
            }

        mObjectRegistry.defineClass(
            objectId,
            info.sourceFileId(),
            info.lineNumber(),
            info.freeVariableMemberAccessChainsToId(),
            baseClassIds);

        return {};
        }
    else {
        return infoOrException.get<std::shared_ptr<PyforaError>>();
        }
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerClassInstance(int64_t objectId, PyObject* pyObject)
    {
    PyObjectPtr classObject = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "__class__"));
    if (classObject == nullptr) {
        throw std::runtime_error(
            "py err in PyObjectWalker::_registerClassInstance: " +
            PyObjectUtils::exc_string()
            );
        }

    auto classIdOrErr = walkPyObject(classObject.get());

    if (classIdOrErr.is<std::shared_ptr<PyforaError>>()) {
        return classIdOrErr.get<std::shared_ptr<PyforaError>>();
        }

    int64_t classId = classIdOrErr.get<int64_t>();

    if (mObjectRegistry.isUnconvertible(classId)) {
        PyObjectPtr modulePathOrNone = PyObjectPtr::unincremented(
            mModuleLevelObjectIndex.getPathToObject(pyObject));
        if (modulePathOrNone == nullptr) {
            throw std::runtime_error(
                "py error in PyObjectWalker::_registerClassInstance: " +
                PyObjectUtils::exc_string()
                );
            }

        mObjectRegistry.defineUnconvertible(
            objectId,
            modulePathOrNone.get()
            );
        return {};
        }

    PyObjectPtr dataMemberNames;
        {
        auto dataMemberNamesOrErr = _getDataMemberNames(pyObject, classObject.get());
        if (not dataMemberNamesOrErr.is<PyObjectPtr>()) {
            return dataMemberNamesOrErr.get<std::shared_ptr<PyforaError>>();
            }

        dataMemberNames = dataMemberNamesOrErr.get<PyObjectPtr>();
        }

    if (dataMemberNames == nullptr) {
        throw std::runtime_error("py error in _registerClassInstance:" +
            PyObjectUtils::exc_string()
            );
        }

    if (not PyList_Check(dataMemberNames.get())) {
        throw std::runtime_error("py error in _registerClassInstance:" +
            PyObjectUtils::exc_string()
            );
        }

    std::map<std::string, int64_t> classMemberNameToClassMemberId;

    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(dataMemberNames.get()); ++ix)
        {
        // borrowed reference
        PyObject* dataMemberName = PyList_GET_ITEM(dataMemberNames.get(), ix);
        if (not PyString_Check(dataMemberName)) {
            throw std::runtime_error("py error in _registerClassInstance:" +
                PyObjectUtils::exc_string()
                );
            }

        PyObjectPtr dataMember = PyObjectPtr::unincremented(
            PyObject_GetAttr(pyObject, dataMemberName));
        if (dataMember == nullptr) {
            throw std::runtime_error("py error in _registerClassInstance:" +
                PyObjectUtils::exc_string()
                );
            }

        auto dataMemberIdOrErr = walkPyObject(dataMember.get());
        
        if (dataMemberIdOrErr.is<std::shared_ptr<PyforaError>>()) {
            return dataMemberIdOrErr.get<std::shared_ptr<PyforaError>>();
            }

        int64_t dataMemberId = dataMemberIdOrErr.get<int64_t>();

        classMemberNameToClassMemberId[
            std::string(
                PyString_AS_STRING(dataMemberName),
                PyString_GET_SIZE(dataMemberName)
                )
            ] = dataMemberId;
        }

    mObjectRegistry.defineClassInstance(
        objectId,
        classId,
        classMemberNameToClassMemberId);

    return {};
    }


variant<PyObjectPtr, std::shared_ptr<PyforaError>>
PyObjectWalker::_getDataMemberNames(PyObject* pyObject, PyObject* classObject) const
    {
    if (PyObject_HasAttrString(pyObject, "__dict__"))
        {
        variant<PyObjectPtr, std::shared_ptr<PyforaError>> tr;

        PyObjectPtr __dict__attr = PyObjectPtr::unincremented(
            PyObject_GetAttrString(pyObject, "__dict__"));
        if (__dict__attr == nullptr) {
            tr.set<PyObjectPtr>(PyObjectPtr());
            return tr;
            }
        if (not PyDict_Check(__dict__attr.get())) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected __dict__ attr to be a dict"
                );
            tr.set<PyObjectPtr>(PyObjectPtr());
            return tr;
            }
        PyObject* keys = PyDict_Keys(__dict__attr.get());
        if (keys == nullptr) {
            tr.set<PyObjectPtr>(PyObjectPtr());
            return tr;
            }
        if (not PyList_Check(keys)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected keys to be a list"
                );
            tr.set<PyObjectPtr>(PyObjectPtr());
            return tr;
            }

        tr.set<PyObjectPtr>(PyObjectPtr::unincremented(keys));
        return tr;
        }
    else {
        return mPyAstUtilModule.collectDataMembersSetInInit(classObject);
        }
    }


PyObject* PyObjectWalker::_withBlockFun(PyObject* withBlock, int64_t lineno) const
    {
    PyObjectPtr sourceText = PyObjectPtr::unincremented(
        PyObject_GetAttrString(withBlock, "sourceText"));
    if (sourceText == nullptr) {
        return nullptr;
        }

    PyObjectPtr sourceTree = PyObjectPtr::unincremented(
        mPyAstUtilModule.pyAstFromText(sourceText.get()));
    if (sourceTree == nullptr) {
        return nullptr;
        }

    PyObjectPtr withBlockAst = PyObjectPtr::unincremented(
        mPyAstUtilModule.withBlockAtLineNumber(
            sourceTree.get(),
            lineno));
    if (withBlockAst == nullptr) {
        return nullptr;
        }

    PyObjectPtr body = PyObjectPtr::unincremented(
        PyObject_GetAttrString(withBlockAst.get(), "body"));
    if (body == nullptr) {
        return nullptr;
        }

    PyObjectPtr argsTuple = PyObjectPtr::unincremented(Py_BuildValue("()"));
    if (argsTuple == nullptr) {
        return nullptr;
        }

    PyObjectPtr ast_args = PyObjectPtr::unincremented(_defaultAstArgs());
    if (ast_args == nullptr) {
        return nullptr;
        }
    
    PyObjectPtr decorator_list = PyObjectPtr::unincremented(PyList_New(0));
    if (decorator_list == nullptr) {
        return nullptr;
        }

    PyObject* kwds = Py_BuildValue("{s:s, s:O, s:O, s:O, s:i, s:i}",
        "name", "",
        "args", ast_args.get(),
        "body", body.get(),
        "decorator_list", decorator_list.get(),
        "lineno", lineno,
        "col_offset", 0);
    if (kwds == nullptr) {
        return nullptr;
        }
        
    return  mAstModule.FunctionDef(argsTuple.get(), kwds);
    }


PyObject* PyObjectWalker::_defaultAstArgs() const
    {
    PyObjectPtr args = PyObjectPtr::unincremented(PyTuple_New(0));
    if (args == nullptr) {
        return nullptr;
        }

    PyObjectPtr emptyList = PyObjectPtr::unincremented(PyList_New(0));
    if (emptyList == nullptr) {
        return nullptr;
        }

    PyObjectPtr kwargs = PyObjectPtr::unincremented(
        Py_BuildValue("{s:O, s:O, s:s, s:s}",
            "args", emptyList.get(),
            "defaults", emptyList.get(),
            "kwarg", nullptr,
            "vararg", nullptr));
    if (kwargs == nullptr) {
        return nullptr;
        }
    
    return mAstModule.arguments(args.get(), kwargs.get());
    }


PyObjectWalker::PyforaErrorOrNull
PyObjectWalker::_registerInstanceMethod(int64_t objectId, PyObject* pyObject)
    {
    PyObjectPtr __self__attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "__self__"));
    if (__self__attr == nullptr) {
        throw std::runtime_error(
            "expected to have a __self__ attr on instancemethods"
            );
        }

    PyObjectPtr __name__attr = PyObjectPtr::unincremented(
        PyObject_GetAttrString(pyObject, "__name__"));
    if (__name__attr == nullptr) {
        throw std::runtime_error(
            "expected to have a __name__ attr on instancemethods"
            );
        }
    if (not PyString_Check(__name__attr.get())) {
        throw std::runtime_error(
            "expected __name__ attr to be a string"
            );
        }

    auto instanceIdOrErr = walkPyObject(__self__attr.get());

    if (instanceIdOrErr.is<int64_t>()) {
        mObjectRegistry.defineInstanceMethod(
            objectId,
            instanceIdOrErr.get<int64_t>(),
            PyObjectUtils::std_string(__name__attr.get())
            );
        return {};
        }
    else {
        return instanceIdOrErr.get<std::shared_ptr<PyforaError>>();
        }
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


UnresolvedFreeVariableExceptions
PyObjectWalker::unresolvedFreeVariableExceptionsModule() const
    {
    return mUnresolvedFreeVariableExceptions;
    }
