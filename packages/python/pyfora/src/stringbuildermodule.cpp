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

#include "StringBuilder.hpp"


/*********************************
Defining a Python C-extension for the C++ class StringBuilder,
from StringBuilder.hpp

cribbed off https://docs.python.org/2.7/extending/newtypes.html
**********************************/

typedef struct {
    PyObject_HEAD
    StringBuilder* nativeStringBuilder;
} PyStringBuilder;


extern "C" {

static PyObject*
PyStringBuilder_new(PyTypeObject* type, PyObject* args, PyObject* kwds)
    {
    PyStringBuilder* self;

    self = (PyStringBuilder*)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->nativeStringBuilder = new StringBuilder();
        }

    return (PyObject*) self;
    }


static void
PyStringBuilder_dealloc(PyStringBuilder* self)
    {
    delete self->nativeStringBuilder;
    self->nativeStringBuilder = 0;
    self->ob_type->tp_free((PyObject*)self);
    }


static int
PyStringBuilder_init(PyStringBuilder* self, PyObject* args, PyObject* kwds)
    {
    return 0;
    }


static PyObject*
PyStringBuilder_addString(PyStringBuilder* self, PyObject* args)
    {
    char* s = NULL;
    int length = -1;

    if (!PyArg_ParseTuple(args, "s#", &s, &length)) {
        return NULL;
        }

    self->nativeStringBuilder->addString(s, length);

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addByte(PyStringBuilder* self, PyObject* args)
    {
    char b = 0;

    if (!PyArg_ParseTuple(args, "b", &b)) {
        return NULL;
        }

    self->nativeStringBuilder->addByte(b);

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addInt32(PyStringBuilder* self, PyObject* args)
    {
    int i = 0;

    if (!PyArg_ParseTuple(args, "i", &i)) {
        return NULL;
        }

    self->nativeStringBuilder->addInt32(i);

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addInt64(PyStringBuilder* self, PyObject* args)
    {
    long int l = 0;

    if (!PyArg_ParseTuple(args, "l", &l)) {
        return NULL;
        }

    self->nativeStringBuilder->addInt64(l);

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addFloat64(PyStringBuilder* self, PyObject* args)
    {
    double d = 0.0;

    if (!PyArg_ParseTuple(args, "d", &d)) {
        return NULL;
        }

    self->nativeStringBuilder->addFloat64(d);

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addInt64s(PyStringBuilder* self, PyObject* args)
    {
    PyObject* obj = NULL;
    PyObject* iterator = NULL;
    PyObject* item = NULL;
    PyObject* exc = NULL;
    std::vector<int64_t> ints;

    if (!PyArg_ParseTuple(args, "O", &obj)) {
        return NULL;
        }

    iterator = PyObject_GetIter(obj);
    if (iterator == NULL) {
        PyErr_SetString(
            PyExc_TypeError,
            "argument must be iterable"
            );
        return NULL;
        }

    while ((item = PyIter_Next(iterator))) {
        if (!PyInt_Check(item)) {
            PyErr_SetString(
                PyExc_TypeError,
                "all elements in the iterable must be integers"
                );
            return NULL;
            }

        ints.push_back(PyInt_AsLong(item));

        Py_XDECREF(item);
        }

    Py_DECREF(iterator);

    self->nativeStringBuilder->addInt64s(ints);

    if ((exc = PyErr_Occurred())) {
        PyErr_SetString(exc, "an error occurred");
        return NULL;
        }

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_addStrings(PyStringBuilder* self, PyObject* args)
    {
    PyObject* obj = NULL;
    PyObject* iterator = NULL;
    PyObject* item = NULL;
    PyObject* exc = NULL;
    std::vector<std::string> strings;
    char* string = NULL;
    Py_ssize_t length = 0;

    if (!PyArg_ParseTuple(args, "O", &obj))
        return NULL;

    iterator = PyObject_GetIter(obj);
    if (iterator == NULL) {
        PyErr_SetString(
            PyExc_TypeError,
            "argument must be iterable"
            );
        return NULL;
        }

    while ((item = PyIter_Next(iterator))) {
        if (PyString_AsStringAndSize(item, &string, &length) == -1)
            {
            PyErr_SetString(
                PyExc_TypeError,
                "all elements in the iterable must be strings"
                );
            return NULL;
            }

        strings.push_back(
            std::string(string, length)
            );

        Py_DECREF(item);
        }

    self->nativeStringBuilder->addStrings(strings);

    Py_DECREF(iterator);

    if ((exc = PyErr_Occurred())) {
        PyErr_SetString(exc, "an error occurred");
        return NULL;
        }

    Py_RETURN_NONE;
    }


static PyObject*
PyStringBuilder_str(PyStringBuilder* self)
    {
    std::string s = self->nativeStringBuilder->str();

    return PyString_FromStringAndSize(s.data(), s.size());
    }


static PyObject*
PyStringBuilder_getbytecount(PyStringBuilder* self, void* closure)
    {
    uint64_t bytecount = self->nativeStringBuilder->bytecount();

    return PyInt_FromSize_t(bytecount);
    }


} // extern "C"

static PyMethodDef PyStringBuilder_methods[] = {
    {"str", (PyCFunction)PyStringBuilder_str, METH_NOARGS,
     "return the underlying string in the builder"},
    {"addString", (PyCFunction)PyStringBuilder_addString, METH_VARARGS,
     "add a string to to buffer"},
    {"addByte", (PyCFunction)PyStringBuilder_addByte, METH_VARARGS,
     "add a byte to to buffer"},
    {"addInt32", (PyCFunction)PyStringBuilder_addInt32, METH_VARARGS,
     "add an Int32 to to buffer"},
    {"addInt64", (PyCFunction)PyStringBuilder_addInt64, METH_VARARGS,
     "add an Int64 to to buffer"},
    {"addFloat64", (PyCFunction)PyStringBuilder_addFloat64, METH_VARARGS,
     "add an Float64 to to buffer"},
    {"addInt64s", (PyCFunction)PyStringBuilder_addInt64s, METH_VARARGS,
     "add an iterable of Int64s to to buffer"},
    {"addStringTuple", (PyCFunction)PyStringBuilder_addStrings, METH_VARARGS,
     "add an iterable of Strings to to buffer"},
    {NULL} /* Sentinel */
    };


static PyMemberDef PyStringBuilder_members[] = {
    {NULL} /* Sentinel */
    };


static PyGetSetDef PyStringBuilder_getsetters[] = {
    {const_cast<char*>("bytecount"),
    (getter)PyStringBuilder_getbytecount,
    0,
     const_cast<char*>("return the accumulated byte count of the buffer"),
     NULL},
    {NULL} /* Sentinel */
    };

static PyTypeObject PyStringBuilderType = {
    PyObject_HEAD_INIT(NULL)
    0,                                         /* ob_size */
    "stringbuilder.StringBuilder",             /* tp_name */
    sizeof(PyStringBuilder),                   /* tp_basicsize */
    0,                                         /* tp_itemsize */
    (destructor)PyStringBuilder_dealloc,       /* tp_dealloc */
    0,                                         /* tp_print */
    0,                                         /* tp_getattr */
    0,                                         /* tp_setattr */
    0,                                         /* tp_compare */
    0,                                         /* tp_repr */
    0,                                         /* tp_as_number */
    0,                                         /* tp_as_sequence */
    0,                                         /* tp_as_mapping */
    0,                                         /* tp_hash */
    0,                                         /* tp_call */
    0,                                         /* tp_str */
    0,                                         /* tp_getattro */
    0,                                         /* tp_setattro */
    0,                                         /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /* tp_flags */
    "StringBuilder objects",                   /* tp_doc */
    0,                                         /* tp_traverse */
    0,                                         /* tp_clear */
    0,                                         /* tp_richcompare */
    0,                                         /* tp_weaklistoffset */
    0,                                         /* tp_iter */
    0,                                         /* tp_iternext */
    PyStringBuilder_methods,                   /* tp_methods */
    PyStringBuilder_members,                   /* tp_members */
    PyStringBuilder_getsetters,                /* tp_getset */
    0,                                         /* tp_base */
    0,                                         /* tp_dict */
    0,                                         /* tp_descr_get */
    0,                                         /* tp_descr_set */
    0,                                         /* tp_dictoffset */
    (initproc)PyStringBuilder_init,            /* tp_init */
    0,                                         /* tp_alloc */
    PyStringBuilder_new,                       /* tp_new */
    };


static PyMethodDef module_methods[] = {
    {NULL}
    };


#ifndef PyMODINIT_FUNC/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif

extern "C" {

PyMODINIT_FUNC
initStringBuilder(void)
    {
    PyObject* m;

    if (PyType_Ready(&PyStringBuilderType) < 0)
        return ;

    m = Py_InitModule3("stringbuilder",
                      module_methods,
                      "expose StringBuilder C++ class");

    if (m == NULL)
        return;

    Py_INCREF(&PyStringBuilderType);
    PyModule_AddObject(
        m,
        "StringBuilder",
        (PyObject*)&PyStringBuilderType);
    }

} // extern "C"

