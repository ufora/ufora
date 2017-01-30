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

#include "pythonObjectRehydratorModule.hpp"
#include <numpy/arrayobject.h>

#include "PyObjectUtils.hpp"
#include "PythonObjectRehydrator.hpp"
#include "core/PyObjectPtr.hpp"

#include <stdexcept>


typedef struct {
    PyObject_HEAD
    PythonObjectRehydrator* nativePythonObjectRehydrator;
} PythonObjectRehydratorStruct;


extern "C" {

static PyObject*
PythonObjectRehydratorStruct_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
    {
    PythonObjectRehydratorStruct* self;

    self = (PythonObjectRehydratorStruct*)type->tp_alloc(type, 0);
    self->nativePythonObjectRehydrator = 0;

    return (PyObject*) self;
    }


static void
PythonObjectRehydratorStruct_dealloc(PythonObjectRehydratorStruct* self)
    {
    delete self->nativePythonObjectRehydrator;
    self->nativePythonObjectRehydrator = 0;
    self->ob_type->tp_free((PyObject*)self);
    }


static int
PythonObjectRehydratorStruct_init(PythonObjectRehydratorStruct* self,
                                  PyObject* args,
                                  PyObject* kwds
                                  )
    {
    int allowUserCodeModuleLevelLookups = 1;
    PyObject* purePythonClassMapping;
    if (!PyArg_ParseTuple(args, "O|i",
                          &purePythonClassMapping,
                          &allowUserCodeModuleLevelLookups))
        {
        return -1;
        }

    self->nativePythonObjectRehydrator = new PythonObjectRehydrator(
        PyObjectPtr::incremented(purePythonClassMapping),
        allowUserCodeModuleLevelLookups
        );

    return 0;
    }


static PyObject*
PythonObjectRehydratorStruct_convertEncodedStringToPythonObject(
        PythonObjectRehydratorStruct* self,
        PyObject* args
        )
    {
    const char* s;
    int s_length;
    int root_id;
    
    if (!PyArg_ParseTuple(args, "s#i", &s, &s_length, &root_id)) {
        return nullptr;
        }

    try {
        return self->nativePythonObjectRehydrator
            ->convertEncodedStringToPythonObject(
                std::string(s, s_length),
                root_id
                );
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
    }


static PyObject*
PythonObjectRehydratorStruct_readFileDescriptorToPythonObject(
        PythonObjectRehydratorStruct* self,
        PyObject* args
        )
    {
    int filedescriptor;
    
    if (!PyArg_ParseTuple(args, "i", &filedescriptor)) {
        return nullptr;
        }

    try {
        return self->nativePythonObjectRehydrator
            ->readFileDescriptorToPythonObject(filedescriptor);
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
    }


} // extern "C"


static PyMethodDef PythonObjectRehydratorStruct_methods[] = {
    {"convertEncodedStringToPythonObject",
     (PyCFunction)PythonObjectRehydratorStruct_convertEncodedStringToPythonObject,
     METH_VARARGS},
    {"readFileDescriptorToPythonObject",
     (PyCFunction)PythonObjectRehydratorStruct_readFileDescriptorToPythonObject,
     METH_VARARGS},
    {nullptr}
    };


static PyMethodDef module_methods[] = {
    {nullptr}
    };


static PyTypeObject PythonObjectRehydratorType = {
    PyObject_HEAD_INIT(nullptr)
    0,                                          /* ob_size */
    "PythonObjectRehydrator.PythonObjectRehydrator",/* tp_name */
    sizeof(PythonObjectRehydratorStruct),             /* tp_basicsize */
    0,                                          /* tp_itemsize */
    (destructor)PythonObjectRehydratorStruct_dealloc, /* tp_dealloc */
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
    PythonObjectRehydratorStruct_methods,             /* tp_methods */
    0,                                          /* tp_members */
    0,                                          /* tp_getset */
    0,                                          /* tp_base */
    0,                                          /* tp_dict */
    0,                                          /* tp_descr_get */
    0,                                          /* tp_descr_set */
    0,                                          /* tp_dictoffset */
    (initproc)PythonObjectRehydratorStruct_init,      /* tp_init */
    0,                                          /* tp_alloc */
    PythonObjectRehydratorStruct_new,                 /* tp_new */
    };


#ifndef PyMODINIT_FUNC/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif


extern "C" {

PyMODINIT_FUNC
initPythonObjectRehydrator()
    {
    if (PyType_Ready(&PythonObjectRehydratorType) < 0) {
        return;
        }

    PyObject* pythonObjectRehydratorModule = 
        Py_InitModule3(
            "PythonObjectRehydrator",
            module_methods,
            "expose PythonObjectRehydrator C++ class"
            );
    if (pythonObjectRehydratorModule == nullptr) {
        return;
        }

    import_array();

    Py_INCREF(&PythonObjectRehydratorType);

    PyModule_AddObject(
        pythonObjectRehydratorModule,
        "PythonObjectRehydrator",
        (PyObject*)&PythonObjectRehydratorType);
    }

} // extern "C"
