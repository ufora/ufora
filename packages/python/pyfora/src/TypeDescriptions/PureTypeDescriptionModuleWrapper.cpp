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
    : mPureTypeDescriptionModule(
        PyObjectPtr::unincremented(
            PyImport_ImportModule(
                "pyfora.TypeDescription"
                )
            )
        )
    {
    if (mPureTypeDescriptionModule == nullptr) {
        throw std::runtime_error(
            "py error instantiating PyFileDescriptionWrapper: " +
            PyObjectUtils::exc_string()
            );
        }
    }


PyObject* PureTypeDescriptionModuleWrapper::pyFileDescription(
        const FileTypeDescription& filedescription
        ) const
    {
    PyObjectPtr pyFileDescriptionClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPureTypeDescriptionModule.get(),
            "File"
            ));
    if (pyFileDescriptionClass == nullptr) {
        return nullptr;
        }

    PyObjectPtr args = PyObjectPtr::unincremented(PyTuple_New(0));
    if (args == nullptr) {
        return nullptr;
        }
    
    PyObjectPtr kw = PyObjectPtr::unincremented(
        Py_BuildValue(
            "{s:s, s:s}",
            "path", filedescription.path().c_str(),
            "text", filedescription.text().c_str()
            ));
    if (kw == nullptr) {
        return nullptr;
        }
    
    return PyObject_Call(
        pyFileDescriptionClass.get(),
        args.get(),
        kw.get()
        );
    }


PyObject* PureTypeDescriptionModuleWrapper::pyHomogeneousListAsNumpyArray(
        const PyObject* array
        ) const
    {
    PyObjectPtr pyHomogeneousListAsNumpyArrayClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            mPureTypeDescriptionModule.get(),
            "HomogenousListAsNumpyArray"
            ));
    if (pyHomogeneousListAsNumpyArrayClass == nullptr) {
        return nullptr;
        }

    return PyObject_CallFunctionObjArgs(
        pyHomogeneousListAsNumpyArrayClass.get(),
        array,
        nullptr
        );
    }
