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
#include <Python.h>
#include <structmember.h>

#include <stdexcept>

#include "BadWithBlockError.hpp"
#include "PyBinaryObjectRegistry.hpp"
#include "PyObjectUtils.hpp"
#include "PyObjectWalker.hpp"
#include "PythonToForaConversionError.hpp"
#include "UnresolvedFreeVariableExceptions.hpp"
#include "UnresolvedFreeVariableExceptionWithTrace.hpp"

/*********************************
Defining a Python C-extension for the C++ class PyObjectWalker,
from PyObjectWalker.hpp

cribbed off https://docs.python.org/2.7/extending/newtypes.html
**********************************/

typedef struct {
    PyObject_HEAD
    PyObjectWalker* binaryObjectRegistry;
    PyObjectWalker* nativePyObjectWalker;
} PyObjectWalkerStruct;


extern "C" {

static PyObject*
PyObjectWalkerStruct_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
    {
    PyObjectWalkerStruct* self;

    self = (PyObjectWalkerStruct*)type->tp_alloc(type, 0);
    self->binaryObjectRegistry = 0;
    self->nativePyObjectWalker = 0;

    return (PyObject*) self;
    }


static void
PyObjectWalkerStruct_dealloc(PyObjectWalkerStruct* self)
    {
    delete self->nativePyObjectWalker;
    self->nativePyObjectWalker = 0;
    self->ob_type->tp_free((PyObject*)self);
    }


namespace {

PyObject* getPythonToForaConversionErrorClass()
    {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    if (pyforaModule == nullptr) {
        return nullptr;
        }

    PyObject* exceptionsModule = PyObject_GetAttrString(pyforaModule, "Exceptions");

    Py_DECREF(pyforaModule);

    if (exceptionsModule == nullptr) {
        return nullptr;
        }

    PyObject* pythonToForaConversionErrorClass = 
        PyObject_GetAttrString(exceptionsModule, "PythonToForaConversionError");

    Py_DECREF(exceptionsModule);

    return pythonToForaConversionErrorClass;
    }


PyObject* getBadWithBlockErrorClass()
    {
    PyObject* pyforaModule = PyImport_ImportModule("pyfora");
    if (pyforaModule == nullptr) {
        return nullptr;
        }

    PyObject* exceptionsModule = PyObject_GetAttrString(pyforaModule, "Exceptions");

    Py_DECREF(pyforaModule);

    if (exceptionsModule == nullptr) {
        return nullptr;
        }

    PyObject* badWithBlockErrorClass = 
        PyObject_GetAttrString(exceptionsModule, "BadWithBlockError");

    Py_DECREF(exceptionsModule);

    return badWithBlockErrorClass;
    }


void translatePythonToForaConversionError(const PythonToForaConversionError& e)
    {
    PyObject* pythonToForaConversionErrorClass = getPythonToForaConversionErrorClass();
    if (pythonToForaConversionErrorClass == nullptr) {
        return;
        }

    PyErr_SetString(
        pythonToForaConversionErrorClass,
        e.what()
        );

    Py_DECREF(pythonToForaConversionErrorClass);
    }


void translateBadWithBlockError(const BadWithBlockError& e) 
    {
    PyObject* badWithBlockErrorClass = getBadWithBlockErrorClass();
    if (badWithBlockErrorClass == nullptr) {
        return;
        }

    PyErr_SetString(
        badWithBlockErrorClass,
        e.what()
        );

    Py_DECREF(badWithBlockErrorClass);
    }

void translateUnresolvedFreeVariableExceptionWithTrace(
    const UnresolvedFreeVariableExceptionWithTrace& e,
    const UnresolvedFreeVariableExceptions& unresolvedFreeVariableExceptionsModule
        )
    {
    PyObject* unresolvedFreeVariableExceptionWithTraceClass =
        unresolvedFreeVariableExceptionsModule
        .getUnresolvedFreeVariableExceptionWithTraceClass();

    if (unresolvedFreeVariableExceptionWithTraceClass == nullptr) {
        return;
        }

    PyObject* value = e.value(); // borrowed reference
    PyErr_SetObject(
        unresolvedFreeVariableExceptionWithTraceClass,
        value
        );
    }

} // anonymous namespace


static int
PyObjectWalkerStruct_init(PyObjectWalkerStruct* self, PyObject* args, PyObject* kwds)
    {
    PyObject* binaryObjectRegistryModule = 
        PyImport_ImportModule("pyfora.BinaryObjectRegistry");
    if (binaryObjectRegistryModule == nullptr) {
        return -1;
        }

    PyObject* binaryObjectRegistryClass = 
        PyObject_GetAttrString(binaryObjectRegistryModule,
                               "BinaryObjectRegistry");

    Py_DECREF(binaryObjectRegistryModule);

    if (binaryObjectRegistryClass == nullptr) {
        return -1;
        }

    if (binaryObjectRegistryClass == nullptr) {
        throw std::runtime_error(
            "couldn't find pyfora.binaryobjectregistry.BinaryObjectRegistry"
            );
        }

    PyObject* purePythonClassMapping;
    if (!PyArg_ParseTuple(args, "OO!",
                          &purePythonClassMapping,
                          binaryObjectRegistryClass,
                          &self->binaryObjectRegistry))
        {
        Py_DECREF(binaryObjectRegistryClass);
        return -1;
        }

    Py_DECREF(binaryObjectRegistryClass);
    
    PyObject* pyObjectWalkerDefaultsModule =
        PyImport_ImportModule("pyfora.PyObjectWalkerDefaults");
    if (pyObjectWalkerDefaultsModule == nullptr) {
        return -1;
        }

    PyObject* excludePredicateFun = PyObject_GetAttrString(
        pyObjectWalkerDefaultsModule,
        "exclude_predicate_fun");
    if (excludePredicateFun == nullptr) {
        Py_DECREF(pyObjectWalkerDefaultsModule);
        return -1;
        }

    PyObject* excludeList = PyObject_GetAttrString(
        pyObjectWalkerDefaultsModule,
        "exclude_list");
    if (excludeList == nullptr) {
        Py_DECREF(excludePredicateFun);
        Py_DECREF(pyObjectWalkerDefaultsModule);
        return -1;
        }

    PyObject* terminalValueFilter = PyObject_GetAttrString(
        pyObjectWalkerDefaultsModule,
        "terminal_value_filter");
    if (terminalValueFilter == nullptr) {
        Py_DECREF(excludeList);
        Py_DECREF(excludePredicateFun);
        Py_DECREF(pyObjectWalkerDefaultsModule);
        return -1;
        }

    PyObject* traceback_type = PyObject_GetAttrString(
        pyObjectWalkerDefaultsModule,
        "traceback_type");
    if (traceback_type == nullptr) {
        Py_DECREF(terminalValueFilter);
        Py_DECREF(excludeList);
        Py_DECREF(excludePredicateFun);
        Py_DECREF(pyObjectWalkerDefaultsModule);
        return -1;
        }

    PyObject* pythonTracebackToJsonFun = PyObject_GetAttrString(
        pyObjectWalkerDefaultsModule,
        "pythonTracebackToJson");
    if (pythonTracebackToJsonFun == nullptr) {
        Py_DECREF(traceback_type);
        Py_DECREF(terminalValueFilter);
        Py_DECREF(excludeList);
        Py_DECREF(excludePredicateFun);
        Py_DECREF(pyObjectWalkerDefaultsModule);
        return -1;
        }

    try {
        self->nativePyObjectWalker = new PyObjectWalker(
            purePythonClassMapping,
            *(((PyBinaryObjectRegistry*)(self->binaryObjectRegistry))->nativeBinaryObjectRegistry),
            excludePredicateFun,
            excludeList,
            terminalValueFilter,
            traceback_type,
            pythonTracebackToJsonFun
            );
        }
    catch (const std::runtime_error& e) {
        std::string err = std::string("error creating a PyObjectWalker: ") + e.what();
        PyErr_SetString(
            PyExc_RuntimeError,
            err.c_str()
            );
        return -1;
        }
    catch (const std::exception& e) {
        std::string err = std::string("error creating a PyObjectWalker: ") + e.what();
        PyErr_SetString(
            PyExc_Exception,
            err.c_str()
            );
        return -1;
        }

    return 0;
    }


static PyObject*
PyObjectWalkerStruct_walkPyObject(PyObjectWalkerStruct* self, PyObject* args)
    {
    PyObject* objToWalk;
    if (!PyArg_ParseTuple(args, "O", &objToWalk)) {
        return nullptr;
        }

    long res;
    try {
        res = self->nativePyObjectWalker->walkPyObject(objToWalk);
        }
    catch (const PythonToForaConversionError& e) {
        translatePythonToForaConversionError(e);
        return nullptr;
        }
    catch (const BadWithBlockError& e) {
        translateBadWithBlockError(e);
        return nullptr;
        }
    catch (const UnresolvedFreeVariableExceptionWithTrace& e) {
        translateUnresolvedFreeVariableExceptionWithTrace(
            e,
            self->nativePyObjectWalker->unresolvedFreeVariableExceptionsModule());
        return nullptr;
        }
    catch (const std::runtime_error& e) {
        PyErr_SetString(
            PyExc_RuntimeError,
            e.what()
            );
        return nullptr;
        }
    catch (const std::exception& e) {
        PyErr_SetString(
            PyExc_Exception,
            e.what()
            );
        return nullptr;
        }

    return PyInt_FromLong(res);
    }


} // extern "C"

static PyMethodDef PyObjectWalkerStruct_methods[] = {
    {"walkPyObject", (PyCFunction)PyObjectWalkerStruct_walkPyObject, METH_VARARGS,
     "walk a python object"},
    {nullptr}
    };


// it seems silly that the name attr in a PyMemberDef isn't a const char*
// AFAIK, it's never modified by python
static PyMemberDef PyObjectWalkerStruct_members[] = {
    {const_cast<char*>("objectRegistry"), T_OBJECT_EX,
     offsetof(PyObjectWalkerStruct, binaryObjectRegistry), 0,
    const_cast<char*>("object registry attribute")},
    {nullptr}
    };


static PyTypeObject PyObjectWalkerStructType = {
    PyObject_HEAD_INIT(nullptr)
    0,                                          /* ob_size */
    "PyObjectWalker.PyObjectWalker",            /* tp_name */
    sizeof(PyObjectWalkerStruct),               /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)PyObjectWalkerStruct_dealloc,   /* tp_dealloc */
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
    "PyObjectWalker objects",                   /* tp_doc */
    0,                                          /* tp_traverse */
    0,                                          /* tp_clear */
    0,                                          /* tp_richcompare */
    0,                                          /* tp_weaklistoffset */
    0,                                          /* tp_iter */
    0,                                          /* tp_iternext */
    PyObjectWalkerStruct_methods,               /* tp_methods */
    PyObjectWalkerStruct_members,               /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)PyObjectWalkerStruct_init,        /* tp_init */
    0,                                          /* tp_alloc */
    PyObjectWalkerStruct_new,                   /* tp_new */
    };


static PyMethodDef module_methods[] = {
    {nullptr}
    };


#ifndef PyMODINIT_FUNC/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif


extern "C" {

PyMODINIT_FUNC
initPyObjectWalker(void)
    {
    PyObject* m;

    if (PyType_Ready(&PyObjectWalkerStructType) < 0)
        return;

    m = Py_InitModule3("PyObjectWalker",
                       module_methods,
                       "expose PyObjectWalker C++ class");

    if (m == nullptr) {
        return;
        }

    Py_INCREF(&PyObjectWalkerStructType);
    PyModule_AddObject(
        m,
        "PyObjectWalker",
        (PyObject*)&PyObjectWalkerStructType);
    }

} // extern "C"
