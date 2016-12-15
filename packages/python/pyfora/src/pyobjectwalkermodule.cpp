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

#include "PyBinaryObjectRegistry.hpp"
#include "PyObjectUtils.hpp"
#include "PyObjectWalker.hpp"
#include "UnresolvedFreeVariableExceptions.hpp"
#include "core/PyObjectPtr.hpp"
#include "core/variant.hpp"
#include "exceptions/PyforaErrors.hpp"

#include <stdexcept>
#include <stdint.h>

/*********************************
Defining a Python C-extension for the C++ class PyObjectWalker,
from PyObjectWalker.hpp

cribbed off https://docs.python.org/2.7/extending/newtypes.html
**********************************/

typedef struct {
    PyObject_HEAD
    PyObject* binaryObjectRegistry;
    PyObjectWalker* nativePyObjectWalker;
} PyObjectWalkerStruct;


extern "C" {

static PyObject*
PyObjectWalkerStruct_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
    {
    PyObjectWalkerStruct* self;

    self = (PyObjectWalkerStruct*)type->tp_alloc(type, 0);
    self->binaryObjectRegistry = nullptr;
    self->nativePyObjectWalker = nullptr;

    return (PyObject*) self;
    }


static void
PyObjectWalkerStruct_dealloc(PyObjectWalkerStruct* self)
    {
    Py_XDECREF(self->binaryObjectRegistry);
    delete self->nativePyObjectWalker;
    self->ob_type->tp_free((PyObject*)self);
    }


static int
PyObjectWalkerStruct_init(PyObjectWalkerStruct* self, PyObject* args, PyObject* kwds)
    {
    PyObjectPtr binaryObjectRegistryModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.BinaryObjectRegistry"));
    if (binaryObjectRegistryModule == nullptr) {
        return -1;
        }

    PyObjectPtr binaryObjectRegistryClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(binaryObjectRegistryModule.get(),
                               "BinaryObjectRegistry")
        );

    if (binaryObjectRegistryClass == nullptr) {
        return -1;
        }

    PyObject* purePythonClassMapping;
    if (!PyArg_ParseTuple(args, "OO!",
                          &purePythonClassMapping,
                          binaryObjectRegistryClass.get(),
                          &self->binaryObjectRegistry))
        {
        return -1;
        }

    Py_INCREF(self->binaryObjectRegistry);
    
    PyObjectPtr pyObjectWalkerDefaultsModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.PyObjectWalkerDefaults"));
    if (pyObjectWalkerDefaultsModule == nullptr) {
        return -1;
        }

    PyObjectPtr excludePredicateFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObjectWalkerDefaultsModule.get(),
            "exclude_predicate_fun"));
    if (excludePredicateFun == nullptr) {
        return -1;
        }

    PyObjectPtr excludeList = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObjectWalkerDefaultsModule.get(),
            "exclude_list"));
    if (excludeList == nullptr) {
        return -1;
        }

    PyObjectPtr terminalValueFilter = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObjectWalkerDefaultsModule.get(),
            "terminal_value_filter"));
    if (terminalValueFilter == nullptr) {
        return -1;
        }

    PyObjectPtr traceback_type = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObjectWalkerDefaultsModule.get(),
            "traceback_type"));
    if (traceback_type == nullptr) {
        return -1;
        }

    PyObjectPtr pythonTracebackToJsonFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            pyObjectWalkerDefaultsModule.get(),
            "pythonTracebackToJson"));
    if (pythonTracebackToJsonFun == nullptr) {
        return -1;
        }

    try {
        self->nativePyObjectWalker = new PyObjectWalker(
            PyObjectPtr::incremented(purePythonClassMapping),
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

    variant<int64_t, std::shared_ptr<PyforaError>> objectIdOrErr;
    try {
        objectIdOrErr = self->nativePyObjectWalker->walkPyObject(objToWalk);
        }
    catch (const UnresolvedFreeVariableExceptionWithTrace& e) {
        e.setPyErr();
        return nullptr;
        }
    catch (const BadWithBlockError& e) {
        e.setPyErr();
        return nullptr;
        }
    catch (const PythonToForaConversionError& e) {
        e.setPyErr();
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

    if (objectIdOrErr.is<int64_t>()) {
        return PyInt_FromLong(objectIdOrErr.get<int64_t>());
        }
    else {
        objectIdOrErr.get<std::shared_ptr<PyforaError>>()->setPyErr();
        return nullptr;
        }
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
