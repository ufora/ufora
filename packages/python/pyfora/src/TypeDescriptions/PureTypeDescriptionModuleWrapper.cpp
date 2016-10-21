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
#include "FileTypeDescription.hpp"
#include "PureTypeDescriptionModuleWrapper.hpp"
#include "../PyObjectUtils.hpp"

#include <stdexcept>


PureTypeDescriptionModuleWrapper::PureTypeDescriptionModuleWrapper()
    : mPureTypeDescriptionModule(nullptr)
    {
    mPureTypeDescriptionModule = PyImport_ImportModule(
        "pyfora.TypeDescription"
        );
    if (mPureTypeDescriptionModule == nullptr) {
        throw std::runtime_error(
            "py error instantiating PyFileDescriptionWrapper: " +
            PyObjectUtils::exc_string()
            );
        }
    }

PyObject* PureTypeDescriptionModuleWrapper::pyFileDescription(
        const FileTypeDescription& filedescription
        )
    {
    PyObject* pyFileDescriptionClass = PyObject_GetAttrString(
        _getInstance().mPureTypeDescriptionModule,
        "File"
        );
    if (pyFileDescriptionClass == nullptr) {
        return nullptr;
        }

    PyObject* args = PyTuple_New(0);
    if (args == nullptr) {
        Py_DECREF(pyFileDescriptionClass);
        return nullptr;
        }
    
    PyObject* kw = Py_BuildValue(
        "{s:s, s:s}",
        "path", filedescription.path().c_str(),
        "text", filedescription.text().c_str()
        );
    if (kw == nullptr) {
        Py_DECREF(args);
        Py_DECREF(pyFileDescriptionClass);
        return nullptr;
        }
    
    PyObject* tr = PyObject_Call(
        pyFileDescriptionClass,
        args,
        kw
        );

    Py_DECREF(kw);
    Py_DECREF(args);
    Py_DECREF(pyFileDescriptionClass);

    return tr;
    }


PyObject* PureTypeDescriptionModuleWrapper::pyHomogeneousListAsNumpyArray(
        const PyObject* array
        )
    {
    PyObject* pyHomogeneousListAsNumpyArrayClass = PyObject_GetAttrString(
        _getInstance().mPureTypeDescriptionModule,
        "HomogenousListAsNumpyArray"
        );
    if (pyHomogeneousListAsNumpyArrayClass == nullptr) {
        return nullptr;
        }

    PyObject* tr = PyObject_CallFunctionObjArgs(
        pyHomogeneousListAsNumpyArrayClass,
        array,
        nullptr
        );

    Py_DECREF(pyHomogeneousListAsNumpyArrayClass);

    return tr;
    }
