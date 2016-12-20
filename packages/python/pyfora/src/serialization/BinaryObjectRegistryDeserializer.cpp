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
#include "../BinaryObjectRegistry.hpp"
#include "../Json.hpp"
#include "../ObjectRegistry.hpp"
#include "../PyObjectUtils.hpp"
#include "../core/PyObjectPtr.hpp"
#include "BinaryObjectRegistryDeserializer.hpp"
#include "DeserializerBase.hpp"

#include <sstream>
#include <stdexcept>


namespace {

bool is_primitive_code(char code)
    {
    return code == BinaryObjectRegistry::CODE_NONE or
        code == BinaryObjectRegistry::CODE_INT or
        code == BinaryObjectRegistry::CODE_LONG or
        code == BinaryObjectRegistry::CODE_FLOAT or
        code == BinaryObjectRegistry::CODE_BOOL or
        code == BinaryObjectRegistry::CODE_STR or
        code == BinaryObjectRegistry::CODE_LIST_OF_PRIMITIVES;
    }

}


void BinaryObjectRegistryDeserializer::deserializeFromStream(
        std::shared_ptr<Deserializer> stream,
        ObjectRegistry& objectRegistry,
        PyObject* convertJsonToObject
        )
    {
    Json jsonModule;

    while (true) {
        int64_t objectId = stream->readInt64();

        if (objectId == -1) {
            return;
            }

        char code = stream->readByte();

        if (is_primitive_code(code))
            {
            PyObjectPtr primitive = PyObjectPtr::unincremented(
                readPrimitive(code, stream));
            if (primitive == nullptr) {
                throw std::runtime_error(
                    std::string("py error reading a primitive in ") +
                    __PRETTY_FUNCTION__ + ":\n" +
                    PyObjectUtils::exc_string()
                    );
                }

            objectRegistry.definePrimitive(objectId, primitive.get());
            }
        else if (code == BinaryObjectRegistry::CODE_TUPLE)
            {
            std::vector<int64_t> objectIds;
            readInt64s(stream, objectIds);
            objectRegistry.defineTuple(objectId, objectIds);
            }
        else if (code == BinaryObjectRegistry::CODE_PACKED_HOMOGENOUS_DATA)
            {
            PyObjectPtr dtype = PyObjectPtr::unincremented(
                readSimplePrimitive(stream));
            if (dtype == nullptr) {
                throw std::runtime_error(
                    "error deserializing packed homogeneous data: " + 
                    PyObjectUtils::exc_string());
                }
            std::string packedBytes = stream->readString();

            objectRegistry.definePackedHomogenousData(
                objectId,
                dtype.get(),
                packedBytes
                );
            }
        else if (code == BinaryObjectRegistry::CODE_LIST) {
            std::vector<int64_t> objectIds;
            readInt64s(stream, objectIds);
            
            objectRegistry.defineList(objectId, objectIds);
            }
        else if (code == BinaryObjectRegistry::CODE_FILE) {
            std::string path = stream->readString();
            std::string text = stream->readString();
            objectRegistry.defineFile(objectId, path, text);
            }
        else if (code == BinaryObjectRegistry::CODE_DICT) {
            std::vector<int64_t> keyIds;
            std::vector<int64_t> valueIds;
            readInt64s(stream, keyIds);
            readInt64s(stream, valueIds);
            objectRegistry.defineDict(objectId, keyIds, valueIds);
            }
        else if (code == BinaryObjectRegistry::CODE_REMOTE_PY_OBJECT) {
            std::string s = stream->readString();
            PyObjectPtr jsonRepresentation = PyObjectPtr::unincremented(
                jsonModule.loads(s));

            PyObjectPtr pyObject = PyObjectPtr::unincremented(
                PyObject_CallFunctionObjArgs(
                    convertJsonToObject,
                    jsonRepresentation.get(),
                    nullptr)
                );
            
            if (pyObject == nullptr) {
                throw std::runtime_error(
                    "error calling convertJsonToObject: " +
                    PyObjectUtils::exc_string()
                    );
                }

            objectRegistry.defineRemotePythonObject(
                objectId,
                pyObject.get());
            }
        else if (code == BinaryObjectRegistry::CODE_BUILTIN_EXCEPTION_INSTANCE) {
            std::string typeName = stream->readString();
            int64_t argsId = stream->readInt64();
            
            objectRegistry.defineBuiltinExceptionInstance(
                objectId,
                typeName,
                argsId);
            }
        else if (code == BinaryObjectRegistry::CODE_NAMED_SINGLETON) {
            std::string singletonName = stream->readString();

            objectRegistry.defineNamedSingleton(objectId, singletonName);
            }
        else if (code == BinaryObjectRegistry::CODE_FUNCTION) {
            int64_t sourceFileId = stream->readInt64();
            int32_t linenumber = stream->readInt32();
            PyObjectPtr freeVariableResolutions = PyObjectPtr::unincremented(
                readFreeVariableResolutions(stream));
            if (freeVariableResolutions == nullptr) {
                throw std::runtime_error(
                    "error processing function: " +
                    PyObjectUtils::exc_string()
                    );
                }

            objectRegistry.defineFunction(
                objectId,
                sourceFileId,
                linenumber,
                freeVariableResolutions.get());
            }
        else if (code == BinaryObjectRegistry::CODE_CLASS) {
            int64_t sourceFileId = stream->readInt64();
            int32_t linenumber = stream->readInt32();
            PyObjectPtr freeVariableResolutions = PyObjectPtr::unincremented(
                readFreeVariableResolutions(stream));
            if (freeVariableResolutions == nullptr) {
                throw std::runtime_error(
                    "error processing class: " +
                    PyObjectUtils::exc_string()
                    );
                }

            std::vector<int64_t> baseClassIds;
            readInt64s(stream, baseClassIds);

            objectRegistry.defineClass(
                objectId,
                sourceFileId,
                linenumber,
                freeVariableResolutions.get(),
                baseClassIds);
            }
        else if (code == BinaryObjectRegistry::CODE_UNCONVERTIBLE) {
            if (stream->readByte()) {
                PyObjectPtr stringTuple = PyObjectPtr::unincremented(
                    readStringTuple(stream));
                if (stringTuple == nullptr) {
                    throw std::runtime_error(
                        "error processing unconvertible: " +
                        PyObjectUtils::exc_string()
                        );
                    }

                objectRegistry.defineUnconvertible(
                    objectId,
                    stringTuple.get());
                }
            else {
                objectRegistry.defineUnconvertible(
                    objectId,
                    Py_None);
                }
            }
        else if (code == BinaryObjectRegistry::CODE_UNRESOLVED_SYMBOL) {
            std::string varname = stream->readString();
            int64_t lineno = stream->readInt64();
            int64_t col_offset = stream->readInt64();

            objectRegistry.defineUnresolvedSymbol(
                objectId,
                varname,
                lineno,
                col_offset);
            }
        else if (code == BinaryObjectRegistry::CODE_CLASS_INSTANCE) {
            int64_t classId = stream->readInt64();
            std::map<std::string, int64_t> classMembers;
            
            int32_t ct = stream->readInt32();
            for (int32_t ix = 0; ix < ct; ++ix) {
                std::string memberName = stream->readString();
                int64_t memberId = stream->readInt64();
                classMembers[memberName] = memberId;
                }

            objectRegistry.defineClassInstance(
                objectId,
                classId,
                classMembers);
            }
        else if (code == BinaryObjectRegistry::CODE_INSTANCE_METHOD) {
            int64_t instanceId = stream->readInt64();
            std::string methodName = stream->readString();

            objectRegistry.defineInstanceMethod(
                objectId,
                instanceId,
                methodName);
            }
        else if (code == BinaryObjectRegistry::CODE_WITH_BLOCK) {
            PyObjectPtr resolutions = PyObjectPtr::unincremented(
                readFreeVariableResolutions(stream));
            if (resolutions == nullptr) {
                throw std::runtime_error(
                    "error getting resolutions: " +
                    PyObjectUtils::exc_string()
                    );
                }

            int64_t sourceFileId = stream->readInt64();
            int32_t linenumber = stream->readInt64();

            objectRegistry.defineWithBlock(
                objectId,
                resolutions.get(),
                sourceFileId,
                linenumber);
            }
        else if (code == BinaryObjectRegistry::CODE_PY_ABORT_EXCEPTION) {
            std::string typeName = stream->readString();
            int64_t argsId = stream->readInt64();
            
            objectRegistry.definePyAbortException(
                objectId,
                typeName,
                argsId);
            }
        else if (code == BinaryObjectRegistry::CODE_STACKTRACE_AS_JSON) {
            std::string stackAsJson = stream->readString();

            PyObjectPtr res = PyObjectPtr::unincremented(
                jsonModule.loads(stackAsJson));
            if (res == nullptr) {
                throw std::runtime_error(
                    "error calling Json::loads: " +
                    PyObjectUtils::exc_string()
                    );
                }

            objectRegistry.defineStacktrace(
                objectId,
                res.get());
            }
        }
    }


void BinaryObjectRegistryDeserializer::readInt64s(
        std::shared_ptr<Deserializer> stream,
        std::vector<int64_t>& ioInts
        )
    {
    int64_t nInts = stream->readInt64();
    for (int64_t ix = 0; ix < nInts; ++ix) {
        ioInts.push_back(stream->readInt64());
        }
    }


PyObject* BinaryObjectRegistryDeserializer::readPrimitive(
        char code,
        std::shared_ptr<Deserializer> stream
        )
    {
    if (code == BinaryObjectRegistry::CODE_NONE) {
        Py_RETURN_NONE;
        }
    if (code == BinaryObjectRegistry::CODE_INT) {
        int64_t id = stream->readInt64();
        return PyInt_FromLong(id);
        }
    if (code == BinaryObjectRegistry::CODE_FLOAT) {
        double d = stream->readFloat64();
        return PyFloat_FromDouble(d);
        }
    if (code == BinaryObjectRegistry::CODE_BOOL) {
        if (stream->readByte()) {
            Py_RETURN_TRUE;
            }
        else {
            Py_RETURN_FALSE;
            }
        }
    if (code == BinaryObjectRegistry::CODE_STR) {
        std::string s = stream->readString();
        return PyString_FromStringAndSize(s.data(), s.size());
        }
    if (code == BinaryObjectRegistry::CODE_LIST_OF_PRIMITIVES) {
        int64_t ct = stream->readInt64();
        PyObject* pyList = PyList_New(ct);
        if (pyList == nullptr) {
            return nullptr;
            }

        for (int64_t ix = 0; ix < ct; ++ix) {
            PyObject* item = readPrimitive(stream->readByte(), stream);

            if (item == nullptr) {
                Py_DECREF(pyList);
                return nullptr;
                }

            PyList_SET_ITEM(pyList, ix, item);
            // setitem steals a reference to item, so we don't need to decref it
            }

        return pyList;
        }
    else {
        std::ostringstream err;
        err << "unknown code: " << (int) code;

        PyErr_SetString(
            PyExc_AssertionError,
            err.str().c_str()
            );

        return nullptr;
        }
    }


PyObject* BinaryObjectRegistryDeserializer::readSimplePrimitive(
        std::shared_ptr<Deserializer> stream)
    {
    char code = stream->readByte();
    
    if (code == BinaryObjectRegistry::CODE_NONE) {
        Py_RETURN_NONE;
        }
    if (code == BinaryObjectRegistry::CODE_INT) {
        int64_t id = stream->readInt64();
        return PyInt_FromLong(id);
        }
    if (code == BinaryObjectRegistry::CODE_STR) {
        std::string s = stream->readString();
        return PyString_FromStringAndSize(s.data(), s.size());
        }
    if (code == BinaryObjectRegistry::CODE_TUPLE) {
        int32_t ct = stream->readInt32();
        PyObject* tup = PyTuple_New(ct);
        if (tup == nullptr) {
            return nullptr;
            }

        for (int32_t ix = 0; ix < ct; ++ix) {
            PyObject* item = readSimplePrimitive(stream);
            if (item == nullptr) {
                Py_DECREF(tup);
                return nullptr;
                }
            
            PyTuple_SET_ITEM(tup, ix, item);
            // setitem steals a reference to item, so we don't need to decref it
            }
        
        return tup;
        }
    if (code == BinaryObjectRegistry::CODE_LIST) {
        int32_t ct = stream->readInt32();
        PyObject* pyList = PyList_New(ct);
        if (pyList == nullptr) {
            return nullptr;
            }

        for (int64_t ix = 0; ix < ct; ++ix) {
            PyObject* item = readSimplePrimitive(stream);

            if (item == nullptr) {
                Py_DECREF(pyList);
                return nullptr;
                }

            PyList_SET_ITEM(pyList, ix, item);
            // setitem steals a reference to item, so we don't need to decref it
            }

        return pyList;
        }
    if (code == BinaryObjectRegistry::CODE_DICT) {
        int32_t ct = stream->readInt32();

        PyObject* d = PyDict_New();
        if (d == nullptr) {
            return nullptr;
            }
    
        for (int32_t ix = 0; ix < ct; ++ix) {
            PyObject* key = readSimplePrimitive(stream);
            if (key == nullptr) {
                Py_DECREF(d);
                return nullptr;
                }
            
            PyObject* value = readSimplePrimitive(stream);
            if (value == nullptr) {
                Py_DECREF(key);
                Py_DECREF(d);
                return nullptr;
                }

            int retcode = PyDict_SetItem(d, key, value);

            Py_DECREF(value);
            Py_DECREF(key);

            if (retcode != 0) {
                Py_DECREF(d);
                return nullptr;
                }
            }

        return d;
        }
    else {
        std::ostringstream err;
        err << "unknown code: " << (int) code;

        PyErr_SetString(
            PyExc_AssertionError,
            err.str().c_str()
            );

        return nullptr;
        }
    }


PyObject* BinaryObjectRegistryDeserializer::readFreeVariableResolutions(
        std::shared_ptr<Deserializer> stream)
    {
    PyObject* d = PyDict_New();
    if (d == nullptr) {
        return nullptr;
        }

    int32_t ct = stream->readInt32();

    for (int32_t ix = 0; ix < ct; ++ix) {
        std::string path = stream->readString();
        int64_t objId = stream->readInt64();

        PyObject* pyObjId = PyInt_FromLong(objId);
        if (pyObjId == nullptr) {
            Py_DECREF(d);
            return nullptr;
            }

        int retcode = PyDict_SetItemString(d, path.c_str(), pyObjId);

        Py_DECREF(pyObjId);

        if (retcode != 0) {
            Py_DECREF(d);
            return nullptr;
            }
        }

    return d;
    }


PyObject* BinaryObjectRegistryDeserializer::readStringTuple(
        std::shared_ptr<Deserializer> stream)
    {
    int32_t ct = stream->readInt32();

    PyObject* tup = PyTuple_New(ct);
    if (tup == nullptr) {
        return nullptr;
        }

    for (int32_t ix = 0; ix < ct; ++ix) {
        std::string item = stream->readString();
        PyObject* pyItem = PyString_FromStringAndSize(item.data(), item.size());
        if (pyItem == nullptr) {
            Py_DECREF(tup);
            return nullptr;
            }

        PyTuple_SET_ITEM(tup, ix, pyItem);
        // PyTuple_SET_ITEM steals a reference to pyItem,
        // so we don't decref it
        }

    return tup;
    }
