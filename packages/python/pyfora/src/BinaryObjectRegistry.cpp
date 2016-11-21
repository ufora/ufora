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

#include "BinaryObjectRegistry.hpp"
#include "FreeVariableMemberAccessChain.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


BinaryObjectRegistry::BinaryObjectRegistry()
    : mNextObjectId(0)
    {
    }
    

void BinaryObjectRegistry::_writePrimitive(PyObject* obj) {
    if (obj == Py_None) {
        mStringBuilder.addByte(CODE_NONE);
        }
    else if (PyBool_Check(obj))
        {
        if (PyObject_IsTrue(obj)) {
            _writePrimitive(true);
            }
        else {
            _writePrimitive(false);
            }
        }
    else if (PyInt_Check(obj)) {
        // TODO: should do a safe conversion here ...
        _writePrimitive((int64_t)PyInt_AS_LONG(obj));
        }
    else if (PyFloat_Check(obj)) {
        _writePrimitive(PyFloat_AS_DOUBLE(obj));
        }
    else if (PyString_Check(obj)) {
        char* s = PyString_AS_STRING(obj);
        Py_ssize_t length = PyString_GET_SIZE(obj);
        
        _writePrimitive(std::string(s, length));
        }
    else if (PyList_Check(obj)) {
        Py_ssize_t length = PyList_GET_SIZE(obj);

        mStringBuilder.addByte(CODE_LIST_OF_PRIMITIVES);
        mStringBuilder.addInt64(length);
        
        for (Py_ssize_t ix = 0; ix < length; ++ix) {
            _writePrimitive(PyList_GET_ITEM(obj, ix));
            }
        }
    else {
        throw std::runtime_error(
            "got an invalid type in _writePrimitive: " + 
            PyObjectUtils::repr_string(obj));
        }
    }


void BinaryObjectRegistry::defineEndOfStream() {
    mStringBuilder.addInt64(-1);
    }


void BinaryObjectRegistry::defineRemotePythonObject(
        int64_t objectId,
        const PyObject* computedValueArg)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_REMOTE_PY_OBJECT);

    std::string data = _computedValueDataString(computedValueArg);
    
    mStringBuilder.addString(data);
    }

void BinaryObjectRegistry::defineUnconvertible(
        int64_t objectId,
        const PyObject* modulePathOrNone)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_UNCONVERTIBLE);

    if (modulePathOrNone == Py_None) {
        mStringBuilder.addByte(0);
        }
    else {
        mStringBuilder.addByte(1);
        mStringBuilder.addStringTuple(modulePathOrNone);
        mUnconvertibleIndices.insert(objectId);
        }
    }


void BinaryObjectRegistry::defineClassInstance(
        int64_t objectId,
        int64_t classId,
        const std::map<std::string, int64_t>& classMemberNameToClassMemberId)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_CLASS_INSTANCE);
    mStringBuilder.addInt64(classId);
    mStringBuilder.addInt32(classMemberNameToClassMemberId.size());
    for (const auto& p: classMemberNameToClassMemberId)
        {
        mStringBuilder.addString(p.first);
        mStringBuilder.addInt64(p.second);
        }
    }


void BinaryObjectRegistry::defineInstanceMethod(int64_t objectId,
                                                int64_t instanceId,
                                                const std::string& methodName)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_INSTANCE_METHOD);
    mStringBuilder.addInt64(instanceId);
    mStringBuilder.addString(methodName);
    }


void BinaryObjectRegistry::definePyAbortException(int64_t objectId,
                                                  const std::string& typeName,
                                                  int64_t argsId)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_PY_ABORT_EXCEPTION);
    mStringBuilder.addString(typeName);
    mStringBuilder.addInt64(argsId);
    }


void BinaryObjectRegistry::_writeFreeVariableResolutions(
        const std::map<FreeVariableMemberAccessChain, int64_t>& chainToId
        )
    {
    mStringBuilder.addInt32(chainToId.size());

    for (const auto& p: chainToId) {
        mStringBuilder.addString(p.first.str());
        mStringBuilder.addInt64(p.second);
        }
    }


void BinaryObjectRegistry::_writeFreeVariableResolutions(
        PyObject* chainToId
        )
    {
    if (not PyDict_Check(chainToId)) {
        throw std::runtime_error(
            "expected a dict in _writeFreeVariableResolutions"
            );
        }

    Py_ssize_t sz = PyDict_Size(chainToId);

    mStringBuilder.addInt32(sz);

    PyObject * key, * value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(chainToId, &pos, &key, &value)) {
        if (not PyString_Check(key)) {
            throw std::runtime_error(
                "expected string keys in _writeFreeVariableResolutions"
                );
            }
        if (not PyInt_Check(value)) {
            throw std::runtime_error(
                "expected it values in _writeFreeVariableResolutions"
                );
            }

        mStringBuilder.addString(
            PyString_AS_STRING(key),
            PyString_GET_SIZE(key)
            );
        mStringBuilder.addInt64(PyInt_AS_LONG(value));
        }
    }


void BinaryObjectRegistry::definePackedHomogenousData(int64_t objectId,
                                                      PyObject* pyObject)
    {
    mStringBuilder.addInt64(objectId);
    mStringBuilder.addByte(CODE_PACKED_HOMOGENOUS_DATA);
    
    PyObject* dtype = PyObject_GetAttrString(pyObject, "dtype");
    if (dtype == nullptr) {
        throw std::runtime_error(
            "py err in BinaryObjectRegistry::definePackedHomogenousData: " +
            PyObjectUtils::format_exc()
            );
        }

    _writeDTypeElement(dtype);
    
    Py_DECREF(dtype);

    PyObject* dataAsBytes = PyObject_GetAttrString(pyObject, "dataAsBytes");
    if (dataAsBytes == nullptr) {
        throw std::runtime_error(
            "py err in BinaryObjectRegistry::definePackedHomogenousData: " +
            PyObjectUtils::format_exc()
            );
        }
    if (not PyString_Check(dataAsBytes)) {
        Py_DECREF(dataAsBytes);
        throw std::runtime_error("expected dataAsBytes attr to be a string");
        }

    mStringBuilder.addString(
        PyString_AS_STRING(dataAsBytes),
        PyString_GET_SIZE(dataAsBytes)
        );
    
    Py_DECREF(dataAsBytes);
    }


void BinaryObjectRegistry::_writeDTypeElement(PyObject* val)
    {
    if (val == Py_None) {
        mStringBuilder.addByte(CODE_NONE);
        }
    else if (PyInt_Check(val)) {
        mStringBuilder.addByte(CODE_INT);
        mStringBuilder.addInt64(PyInt_AS_LONG(val));
        }
    else if (PyString_Check(val)) {
        mStringBuilder.addByte(CODE_STR);
        mStringBuilder.addString(
            PyString_AS_STRING(val),
            PyString_GET_SIZE(val)
            );
        }
    else if (PyTuple_Check(val)) {
        mStringBuilder.addByte(CODE_TUPLE);
        Py_ssize_t len = PyTuple_GET_SIZE(val);
        mStringBuilder.addInt32(len);
        for (Py_ssize_t ix = 0; ix < len; ++ix) {
            _writeDTypeElement(PyTuple_GET_ITEM(val, ix));
            }
        }
    else {
        throw std::runtime_error("unknown primitive in dtype: " +
            PyObjectUtils::str_string(val));
        }
    }


std::string BinaryObjectRegistry::_computedValueDataString(
        const PyObject* computedValueArg
        ) const
    {
    PyObject* res = mBinaryObjectRegisteryHelpers.computedValueDataString(
        computedValueArg);
    if (res == nullptr) {
        throw std::runtime_error(
            "py error getting computedValueDataString in "
            "BinaryObjectRegistry::_computedValueDataString: " +
            PyObjectUtils::exc_string());
        }
    
    std::string tr = std::string(
        PyString_AS_STRING(res),
        PyString_GET_SIZE(res)
        );

    Py_DECREF(res);

    return tr;
    }


