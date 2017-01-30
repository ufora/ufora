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
#include "PyBinaryObjectRegistry.hpp"
#include <structmember.h>

#include "BinaryObjectRegistry.hpp"
#include "FreeVariableMemberAccessChain.hpp"
#include "PyObjectWalker.hpp"
#include "PyObjectUtils.hpp"

#include <iostream>
#include <stdexcept>

/*********************************
Defining a Python C-extension for the C++ class BinaryObjectRegistry,
from BinaryObjectRegistry.hpp

cribbed off https://docs.python.org/2.7/extending/newtypes.html
**********************************/



extern "C" {

static PyObject*
PyBinaryObjectRegistry_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
    {
    PyBinaryObjectRegistry* self;

    self = (PyBinaryObjectRegistry*)type->tp_alloc(type, 0);
    if (self != nullptr) {
        self->nativeBinaryObjectRegistry = new BinaryObjectRegistry();
        }

    return (PyObject*) self;
    }


static void
PyBinaryObjectRegistry_dealloc(PyBinaryObjectRegistry* self)
    {
    delete self->nativeBinaryObjectRegistry;
    self->ob_type->tp_free((PyObject*)self);
    }


static int
PyBinaryObjectRegistry_init(PyBinaryObjectRegistry* self, PyObject* args, PyObject* kwds)
    {
    return 0;
    }


static PyObject*
PyBinaryObjectRegistry_str(PyBinaryObjectRegistry* self)
    {
    std::string s = self->nativeBinaryObjectRegistry->str();

    return PyString_FromStringAndSize(s.data(), s.size());
    }


static PyObject*
PyBinaryObjectRegistry_defineEndOfStream(PyBinaryObjectRegistry* self,
                                         PyObject* args)
    {
    self->nativeBinaryObjectRegistry->defineEndOfStream();

    Py_RETURN_NONE;
    }


static PyObject*
PyBinaryObjectRegistry_clear(PyBinaryObjectRegistry* self,
                             PyObject* args)
    {
    self->nativeBinaryObjectRegistry->clear();

    Py_RETURN_NONE;
    }


static PyObject*
PyBinaryObjectRegistry_allocateObject(PyBinaryObjectRegistry* self,
                                      PyObject* args)
    {
    int64_t id = self->nativeBinaryObjectRegistry->allocateObject();

    return PyInt_FromLong(id);
    }


static PyObject*
PyBinaryObjectRegistry_definePrimitive(PyBinaryObjectRegistry* self,
                                       PyObject* args)
    {
    int objectId;
    PyObject* primitive;

    if (!PyArg_ParseTuple(args, "iO", &objectId, &primitive)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->definePrimitive(objectId, primitive);

    Py_RETURN_NONE;
    }


static PyObject*
PyBinaryObjectRegistry_defineTuple(PyBinaryObjectRegistry* self,
                                   PyObject* args)
    {
    int objectId;
    PyObject* tuple;

    if (!PyArg_ParseTuple(args, "iO!", &objectId, &PyTuple_Type, &tuple)) {
        return nullptr;
        }

    std::vector<int64_t> memberIds;
    for (Py_ssize_t ix = 0; ix < PyTuple_GET_SIZE(tuple); ++ix) {
        PyObject* item = PyTuple_GET_ITEM(tuple, ix);
        if (not PyInt_Check(item)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected ints in the tuple"
                );
            return nullptr;
            }
        memberIds.push_back(PyInt_AS_LONG(item));        
        }

    self->nativeBinaryObjectRegistry->defineTuple(
        objectId,
        memberIds);

    Py_RETURN_NONE;
    }


static PyObject*
PyBinaryObjectRegistry_defineList(PyBinaryObjectRegistry* self,
                                  PyObject* args)
    {
    int objectId;
    PyObject* list;

    if (!PyArg_ParseTuple(args, "iO!", &objectId, &PyList_Type, &list)) {
        return nullptr;
        }

    std::vector<int64_t> memberIds;
    for (Py_ssize_t ix = 0; ix < PyList_GET_SIZE(list); ++ix) {
        PyObject* item = PyList_GET_ITEM(list, ix);
        if (not PyInt_Check(item)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected ints in the list"
                );
            return nullptr;
            }
        memberIds.push_back(PyInt_AS_LONG(item));        
        }

    self->nativeBinaryObjectRegistry->defineList(
        objectId,
        memberIds);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineDict(PyBinaryObjectRegistry* self,
                                  PyObject* args)
    {
    int objectId;
    PyObject* pyKeyIds;
    PyObject* pyValueIds;

    if (!PyArg_ParseTuple(args,
                          "iO!O!",
                          &objectId,
                          &PyList_Type,
                          &pyKeyIds,
                          &PyList_Type,
                          &pyValueIds)) {
        return nullptr;
        }

    Py_ssize_t list_len = PyList_GET_SIZE(pyKeyIds);

    if (list_len != PyList_GET_SIZE(pyValueIds)) {
        PyErr_SetString(
            PyExc_AssertionError,
            "keyIds list must have the same size as valueIds"
            );
        return nullptr;
        }

    std::vector<int64_t> keyIds;
    std::vector<int64_t> valueIds;

    for (Py_ssize_t ix = 0; ix < list_len; ++ix) {
        // getitems are borrowed references
        PyObject* key = PyList_GET_ITEM(pyKeyIds, ix);
        PyObject* value = PyList_GET_ITEM(pyValueIds, ix);

        if (not PyInt_Check(key)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int keys"
                );
            return nullptr;
            }
        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int values"
                );
            return nullptr;
            }

        keyIds.push_back(PyInt_AS_LONG(key));
        valueIds.push_back(PyInt_AS_LONG(value));
        }

    self->nativeBinaryObjectRegistry->defineDict(
        objectId,
        keyIds,
        valueIds);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineRemotePythonObject(PyBinaryObjectRegistry* self,
                                                PyObject* args)
    {
    int objectId;
    PyObject* computedValueArg;

    if (!PyArg_ParseTuple(args, "iO", &objectId, &computedValueArg)) {

        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineRemotePythonObject(
        objectId,
        computedValueArg);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineBuiltinExceptionInstance(
        PyBinaryObjectRegistry* self,
        PyObject* args)
    {
    int objectId;
    const char* typeName;
    int typeNameSize;
    int argsId;

    if (!PyArg_ParseTuple(args, "is#i",
            &objectId, 
            &typeName,
            &typeNameSize,
            &argsId)) {
        return nullptr;
        }
    
    self->nativeBinaryObjectRegistry->defineBuiltinExceptionInstance(
        objectId,
        typeName,
        typeNameSize,
        argsId);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineNamedSingleton(
        PyBinaryObjectRegistry* self,
        PyObject* args)
    {
    int objectId;
    const char* singletonName;
    int singletonNameSize;

        if (!PyArg_ParseTuple(args,
                              "is#",
                              &objectId,
                              &singletonName,
                              &singletonNameSize)) {
        return nullptr;
        }
    
    self->nativeBinaryObjectRegistry->defineNamedSingleton(
        objectId,
        singletonName,
        singletonNameSize
        );

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineFunction(
        PyBinaryObjectRegistry* self,
        PyObject* args
        )
    {
    int objectId;
    int sourceFileId;
    int linenumber;
    PyObject* pyChainToId;

    if (!PyArg_ParseTuple(args,
                          "iiiO!",
                          &objectId,
                          &sourceFileId,
                          &linenumber,
                          &PyDict_Type,
                          &pyChainToId)) {
        return nullptr;
        }

    std::map<FreeVariableMemberAccessChain, int64_t> chainToId;

    PyObject * key, * value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(pyChainToId, &pos, &key, &value)) {
        FreeVariableMemberAccessChain chain;
        try {
            chain = PyObjectWalker::toChain(key);
            }
        catch (const std::runtime_error& e) {
            PyErr_SetString(
                PyExc_TypeError,
                e.what()
                );
            return nullptr;
            }

        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int values"
                );
            return nullptr;
            }

        chainToId[chain] = PyInt_AS_LONG(value);
        }

    self->nativeBinaryObjectRegistry->defineFunction(
        objectId,
        sourceFileId,
        linenumber,
        chainToId);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineClass(
        PyBinaryObjectRegistry* self,
        PyObject* args
        )
    {
    int objectId;
    int sourceFileId;
    int linenumber;
    PyObject* pyChainToId;
    PyObject* pyBaseClassIds;

    if (!PyArg_ParseTuple(args,
                          "iiiO!O!",
                          &objectId,
                          &sourceFileId,
                          &linenumber,
                          &PyDict_Type,
                          &pyChainToId,
                          &PyTuple_Type,
                          &pyBaseClassIds)) {
        return nullptr;
        }

    std::map<FreeVariableMemberAccessChain, int64_t> chainToId;

    PyObject * key, * value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(pyChainToId, &pos, &key, &value)) {
        FreeVariableMemberAccessChain chain;
        try {
            chain = PyObjectWalker::toChain(key);
            }
        catch (const std::runtime_error& e) {
            PyErr_SetString(
                PyExc_TypeError,
                e.what()
                );
            return nullptr;
            }

        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int values"
                );
            return nullptr;
            }

        chainToId[chain] = PyInt_AS_LONG(value);
        }

    std::vector<int64_t> baseClassIds;
    for (Py_ssize_t ix = 0; ix < PyTuple_GET_SIZE(pyBaseClassIds); ++ix) {
        PyObject* item = PyTuple_GET_ITEM(pyBaseClassIds, ix);
        if (not PyInt_Check(item)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int base class ids"
                );
            return nullptr;
            }
        baseClassIds.push_back(PyInt_AS_LONG(item));
        }

    self->nativeBinaryObjectRegistry->defineClass(
        objectId,
        sourceFileId,
        linenumber,
        chainToId,
        baseClassIds);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineUnconvertible(PyBinaryObjectRegistry* self,
                                           PyObject* args)
    {
    int objectId;
    PyObject* modulePathOrNone;

    if (!PyArg_ParseTuple(args, "iO", &objectId, &modulePathOrNone)) {

        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineUnconvertible(
        objectId,
        modulePathOrNone);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineClassInstance(PyBinaryObjectRegistry* self,
                                           PyObject* args)
    {
    int objectId;
    int classId;
    PyObject* pyClassMemberNameToClassMemberId;
    
    if (!PyArg_ParseTuple(args,
            "iiO!",
            &objectId, 
            &classId,
            &PyDict_Type,
            &pyClassMemberNameToClassMemberId)) {
        return nullptr;
        }
        
    PyObject * key, * value;
    Py_ssize_t pos = 0;

    std::map<std::string, int64_t> classMemberNameToClassMemberId;
    while (PyDict_Next(pyClassMemberNameToClassMemberId,
            &pos, &key, &value)) {
        if (not PyString_Check(key)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected string keys"
                );
            return nullptr;
            }
        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int values"
                );
            }
        
        classMemberNameToClassMemberId[
            std::string(
                PyString_AS_STRING(key),
                PyString_GET_SIZE(key)
                )] = PyInt_AS_LONG(value);
        }

    self->nativeBinaryObjectRegistry->defineClassInstance(
        objectId,
        classId,
        classMemberNameToClassMemberId);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineInstanceMethod(PyBinaryObjectRegistry* self,
                                            PyObject* args)
    {
    int objectId;
    int instanceId;
    const char* methodName;
    int methodNameSize;

    if (!PyArg_ParseTuple(args, "iis#",
            &objectId,
            &instanceId,
            &methodName,
            &methodNameSize)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineInstanceMethod(
        objectId,
        instanceId,
        std::string(methodName, methodNameSize)
        );

    Py_RETURN_NONE;
    }        


PyObject*
PyBinaryObjectRegistry_defineWithBlock(
        PyBinaryObjectRegistry* self,
        PyObject* args
        )
    {
    int objectId;
    PyObject* pyChainToId;
    int sourceFileId;
    int linenumber;

    if (!PyArg_ParseTuple(args,
                          "iO!ii",
                          &objectId,
                          &PyDict_Type,
                          &pyChainToId,
                          &sourceFileId,
                          &linenumber)) {
        return nullptr;
        }

    std::map<FreeVariableMemberAccessChain, int64_t> chainToId;

    PyObject * key, * value;
    Py_ssize_t pos = 0;

    while (PyDict_Next(pyChainToId, &pos, &key, &value)) {
        FreeVariableMemberAccessChain chain;
        try {
            chain = PyObjectWalker::toChain(key);
            }
        catch (const std::runtime_error& e) {
            PyErr_SetString(
                PyExc_TypeError,
                e.what()
                );
            return nullptr;
            }

        if (not PyInt_Check(value)) {
            PyErr_SetString(
                PyExc_TypeError,
                "expected int values"
                );
            return nullptr;
            }

        chainToId[chain] = PyInt_AS_LONG(value);
        }

    self->nativeBinaryObjectRegistry->defineWithBlock(
        objectId,
        chainToId,
        sourceFileId,
        linenumber);

    Py_RETURN_NONE;
    }


PyObject* 
PyBinaryObjectRegistry_definePyAbortException(PyBinaryObjectRegistry* self,
                                              PyObject* args)
    {
    int objectId;
    const char* typeName;
    int typeNameSize;
    int argsId;

    if (not PyArg_ParseTuple(args,
                             "is#i",
                             &objectId,
                             &typeName,
                             &typeNameSize,
                             &argsId)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->definePyAbortException(
        objectId,
        std::string(typeName, typeNameSize),
        argsId);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_definePackedHomogeneousData(PyBinaryObjectRegistry* self,
                                                   PyObject* args)
    {
    int objectId;
    PyObject* val;

    if (!PyArg_ParseTuple(args, "iO", &objectId, &val)) {
        return nullptr;
        }

    try {
        self->nativeBinaryObjectRegistry->definePackedHomogenousData(
            objectId,
            val);
        }
    catch (const std::runtime_error& e) {
        PyErr_SetString(
            PyExc_TypeError,
            e.what()
            );
        }

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineFile(PyBinaryObjectRegistry* self,
                                  PyObject* args)
    {
    int objectId;
    const char* textStr;
    int textStrSize;
    const char* pathStr;
    int pathStrSize;

    if (!PyArg_ParseTuple(args,
                          "is#s#",
                          &objectId,
                          &textStr,
                          &textStrSize,
                          &pathStr,
                          &pathStrSize)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineFile(
        objectId,
        std::string(textStr, textStrSize),
        std::string(pathStr, pathStrSize)
        );

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineUnresolvedVarWithPosition(
        PyBinaryObjectRegistry* self,
        PyObject* args
        )
    {
    int objectId, lineno, col_offset, varname_len;
    const char* varname;
    
    if (!PyArg_ParseTuple(args,
                          "is#ii",
                          &objectId,
                          &varname,
                          &varname_len,
                          &lineno,
                          &col_offset)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineUnresolvedVarWithPosition(
        objectId,
        std::string(varname, varname_len),
        lineno,
        col_offset);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_defineStacktrace(PyBinaryObjectRegistry* self,
                                        PyObject* args)
    {
    int objectId;
    PyObject* stackTraceAsJsonOrNone;

    if (!PyArg_ParseTuple(args, "iO", &objectId, &stackTraceAsJsonOrNone)) {
        return nullptr;
        }

    self->nativeBinaryObjectRegistry->defineStacktrace(
        objectId,
        stackTraceAsJsonOrNone);

    Py_RETURN_NONE;
    }


PyObject*
PyBinaryObjectRegistry_bytecount(PyBinaryObjectRegistry* self,
                                 PyObject* args)
    {
    return PyInt_FromLong(self->nativeBinaryObjectRegistry->bytecount());
    }
        

} // extern "C"


static PyMethodDef PyBinaryObjectRegistry_methods[] = {
    {"bytecount",
     (PyCFunction)PyBinaryObjectRegistry_bytecount,
     METH_NOARGS},    
    {"str",
     (PyCFunction)PyBinaryObjectRegistry_str,
     METH_NOARGS,
     "return the underlying string in the buffer"},
    {"defineEndOfStream",
     (PyCFunction)PyBinaryObjectRegistry_defineEndOfStream,
     METH_NOARGS,
     "define the end of the stream"},
    {"clear",
     (PyCFunction)PyBinaryObjectRegistry_clear,
     METH_NOARGS,
     "clear the underlying string"},
    {"allocateObject",
     (PyCFunction)PyBinaryObjectRegistry_allocateObject,
     METH_NOARGS},
    {"definePrimitive",
     (PyCFunction)PyBinaryObjectRegistry_definePrimitive,
     METH_VARARGS},
    {"defineTuple",
     (PyCFunction)PyBinaryObjectRegistry_defineTuple,
     METH_VARARGS},
    {"defineList",
     (PyCFunction)PyBinaryObjectRegistry_defineList,
     METH_VARARGS},
    {"defineDict",
     (PyCFunction)PyBinaryObjectRegistry_defineDict,
     METH_VARARGS},
    {"defineRemotePythonObject",
     (PyCFunction)PyBinaryObjectRegistry_defineRemotePythonObject,
     METH_VARARGS},
    {"defineBuiltinExceptionInstance",
     (PyCFunction)PyBinaryObjectRegistry_defineBuiltinExceptionInstance,
     METH_VARARGS},
    {"defineNamedSingleton",
     (PyCFunction)PyBinaryObjectRegistry_defineNamedSingleton,
     METH_VARARGS},
    {"defineFunction",
     (PyCFunction)PyBinaryObjectRegistry_defineFunction,
     METH_VARARGS},
    {"defineClass",
     (PyCFunction)PyBinaryObjectRegistry_defineClass,
     METH_VARARGS},
    {"defineUnconvertible",
     (PyCFunction)PyBinaryObjectRegistry_defineUnconvertible,
     METH_VARARGS},
    {"defineClassInstance",
     (PyCFunction)PyBinaryObjectRegistry_defineClassInstance,
     METH_VARARGS},
    {"defineInstanceMethod",
     (PyCFunction)PyBinaryObjectRegistry_defineInstanceMethod,
     METH_VARARGS},
    {"defineWithBlock",
     (PyCFunction)PyBinaryObjectRegistry_defineWithBlock,
     METH_VARARGS},
    {"definePyAbortException",
     (PyCFunction)PyBinaryObjectRegistry_definePyAbortException,
     METH_VARARGS},
    {"definePackedHomogenousData",
     (PyCFunction)PyBinaryObjectRegistry_definePackedHomogeneousData,
     METH_VARARGS},
    {"defineFile",
     (PyCFunction)PyBinaryObjectRegistry_defineFile,
     METH_VARARGS},
    {"defineStacktrace",
     (PyCFunction)PyBinaryObjectRegistry_defineStacktrace,
     METH_VARARGS},
    {"defineUnresolvedVarWithPosition",
     (PyCFunction)PyBinaryObjectRegistry_defineUnresolvedVarWithPosition,
     METH_VARARGS},
    {nullptr} /* Sentinel */
    };


static PyTypeObject PyBinaryObjectRegistryType = {
    PyObject_HEAD_INIT(nullptr)
    0,                                          /* ob_size */
    "BinaryObjectRegistry.BinaryObjectRegistry",/* tp_name */
    sizeof(PyBinaryObjectRegistry),             /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)PyBinaryObjectRegistry_dealloc, /* tp_dealloc */
    0,                                          /* tp_print */
    0,                                          /* tp_getattr */
    0,                                          /* tp_setattr */
    0,                                          /* tp_compare */
    0,                                          /* tp_repr */
    0,                                          /* tp_as_number */
    0,                                          /* tp_as_sequence */
    0,                                          /* tp_as_mapping */
    0,                                          /* tp_hash */
    0,                                          /* tp_call */
    0,                                          /* tp_str */
    0,                                          /* tp_getattro */
    0,                                          /* tp_setattro */
    0,                                          /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,   /* tp_flags */
    "BinaryObjectRegistry objects",             /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    PyBinaryObjectRegistry_methods,             /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)PyBinaryObjectRegistry_init,      /* tp_init */
    0,                                          /* tp_alloc */
    PyBinaryObjectRegistry_new,                 /* tp_new */
    };


static PyMethodDef module_methods[] = {
    {nullptr}
    };


#ifndef PyMODINIT_FUNC/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

namespace {
//returns 0 on success, -1 otherwise
int _initBinaryObjectRegistryCodes(PyObject* binaryObjectRegistryModule)
    {
    return PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_NONE", BinaryObjectRegistry::CODE_NONE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_INT", BinaryObjectRegistry::CODE_INT) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_LONG", BinaryObjectRegistry::CODE_LONG) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_FLOAT", BinaryObjectRegistry::CODE_FLOAT) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_BOOL", BinaryObjectRegistry::CODE_BOOL) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_STR", BinaryObjectRegistry::CODE_STR) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_LIST_OF_PRIMITIVES", BinaryObjectRegistry::CODE_LIST_OF_PRIMITIVES) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_TUPLE", BinaryObjectRegistry::CODE_TUPLE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_PACKED_HOMOGENOUS_DATA", BinaryObjectRegistry::CODE_PACKED_HOMOGENOUS_DATA) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_LIST", BinaryObjectRegistry::CODE_LIST) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_FILE", BinaryObjectRegistry::CODE_FILE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_DICT", BinaryObjectRegistry::CODE_DICT) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_REMOTE_PY_OBJECT", BinaryObjectRegistry::CODE_REMOTE_PY_OBJECT) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_BUILTIN_EXCEPTION_INSTANCE", BinaryObjectRegistry::CODE_BUILTIN_EXCEPTION_INSTANCE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_NAMED_SINGLETON", BinaryObjectRegistry::CODE_NAMED_SINGLETON) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_FUNCTION", BinaryObjectRegistry::CODE_FUNCTION) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_CLASS", BinaryObjectRegistry::CODE_CLASS) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_UNCONVERTIBLE", BinaryObjectRegistry::CODE_UNCONVERTIBLE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_CLASS_INSTANCE", BinaryObjectRegistry::CODE_CLASS_INSTANCE) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_INSTANCE_METHOD", BinaryObjectRegistry::CODE_INSTANCE_METHOD) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_WITH_BLOCK", BinaryObjectRegistry::CODE_WITH_BLOCK) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_PY_ABORT_EXCEPTION", BinaryObjectRegistry::CODE_PY_ABORT_EXCEPTION) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_STACKTRACE_AS_JSON", BinaryObjectRegistry::CODE_STACKTRACE_AS_JSON) or
        PyModule_AddIntConstant(binaryObjectRegistryModule, "CODE_UNRESOLVED_SYMBOL", BinaryObjectRegistry::CODE_UNRESOLVED_SYMBOL);
    }
}

extern "C" {

PyMODINIT_FUNC
initBinaryObjectRegistry()
    {
    PyObject* binaryObjectRegistryModule;

    if (PyType_Ready(&PyBinaryObjectRegistryType) < 0) {
        return;
        }

    binaryObjectRegistryModule = Py_InitModule3(
        "BinaryObjectRegistry",
        module_methods,
        "expose BinaryObjectRegistry C++ class");
    if (binaryObjectRegistryModule == nullptr) {        
        return;
        }

    if (_initBinaryObjectRegistryCodes(binaryObjectRegistryModule)) {
        std::cout << "error initializing code attributes on BinaryObjectRegistry" << std::endl;
        return;
        }

    Py_INCREF(&PyBinaryObjectRegistryType);
    PyModule_AddObject(
        binaryObjectRegistryModule,
        "BinaryObjectRegistry",
        (PyObject*)&PyBinaryObjectRegistryType);
    }

} // extern "C"
