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
#include "../pythonObjectRehydratorModule.hpp"
#define NO_IMPORT_ARRAY
#include <numpy/arrayobject.h>

#include "../IRToPythonConverter.hpp"
#include "../PyObjectUtils.hpp"
#include "PackedHomogenousDataTypeDescription.hpp"
#include "PureTypeDescriptionModuleWrapper.hpp"

#include <stdexcept>


PackedHomogenousDataTypeDescription::PackedHomogenousDataTypeDescription(
        PyObject* dtype,
        const std::string& packedBytes
        )
    : mDtype(dtype),
      mPackedBytes(packedBytes)
    {
    Py_XINCREF(mDtype);
    }


PackedHomogenousDataTypeDescription::~PackedHomogenousDataTypeDescription()
    {
    Py_XDECREF(mDtype);
    }
    

namespace {

// returns a new reference
PyObject* primitiveToDtypeArg(PyObject* primitive)
    {
    if (primitive == Py_None) {
        Py_INCREF(primitive);
        return primitive;
        }

    if (PyString_Check(primitive)) {
        Py_INCREF(primitive);
        return primitive;
        }

    PyObject* iterator = PyObject_GetIter(primitive);
    if (iterator == nullptr) {
        return nullptr;
        }

    PyObject* pyList = PyList_New(0);
    if (pyList == nullptr) {
        return nullptr;
        }

    PyObject* item;
    while ((item = PyIter_Next(iterator))) {
        PyObject* dtypeArg = primitiveToDtypeArg(item);
        if (dtypeArg == nullptr) {
            Py_DECREF(item);
            Py_DECREF(pyList);
            Py_DECREF(iterator);
            return nullptr;
            }

        PyObject* tup = PyTuple_New(2);
        if (tup == nullptr) {
            Py_DECREF(dtypeArg);
            Py_DECREF(item);
            Py_DECREF(pyList);
            Py_DECREF(iterator);
            return nullptr;
            }

        PyObject* pyString = PyString_FromString("");
        if (pyString == nullptr) {
            Py_DECREF(tup);
            Py_DECREF(dtypeArg);
            Py_DECREF(item);
            Py_DECREF(pyList);
            Py_DECREF(iterator);
            return nullptr;
            }

        // these steal references to the item inserted, 
        // so decrefing isn't necessary
        PyTuple_SET_ITEM(tup, 0, pyString);
        PyTuple_SET_ITEM(tup, 1, dtypeArg);
        
        int retcode = PyList_Append(pyList, tup);
        
        Py_DECREF(tup);
        Py_DECREF(item);

        if (retcode < 0) {
            Py_DECREF(pyList);
            Py_DECREF(iterator);
            return nullptr;
            }
        }

    Py_DECREF(iterator);

    return pyList;
    }

PyArray_Descr* primitiveToDtype(PyObject* primitive)
    {
    PyArray_Descr* tr;

    PyObject* dTypeArg = primitiveToDtypeArg(primitive);
    if (dTypeArg == nullptr) {
        return nullptr;
        }

    int retcode = PyArray_DescrConverter(dTypeArg, &tr);

    Py_DECREF(dTypeArg);

    if (retcode < 0) {
        return nullptr;
        }

    return tr;
    }

}


PyObject* PackedHomogenousDataTypeDescription::transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyArray_Descr* dtype = primitiveToDtype(mDtype);
    if (dtype == nullptr) {
        return nullptr;
        }

    // does this steal a reference to dtype??
    PyObject* array = PyArray_FromString(const_cast<char*>(mPackedBytes.data()),
                                         mPackedBytes.size(),
                                         dtype,
                                         -1,
                                         nullptr);

    if (retainHomogenousListsAsNumpy) {
        PyObject* packedHomogeneousDataInstance =
            PureTypeDescriptionModuleWrapper::pyHomogeneousListAsNumpyArray(array);

        Py_DECREF(array);

        return packedHomogeneousDataInstance;
        }
    else {
        PyObject* list = PyArray_ToList((PyArrayObject*)array);
        Py_DECREF(array);

        return list;
        }
    }

