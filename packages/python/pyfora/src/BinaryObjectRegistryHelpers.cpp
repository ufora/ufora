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
#include "BinaryObjectRegistryHelpers.hpp"
#include "PyObjectUtils.hpp"

#include <stdexcept>


BinaryObjectRegistryHelpers::BinaryObjectRegistryHelpers() :
        mComputedValueDataStringFun(0)
    {
    PyObject* binaryObjectRegistryHelpersModule = PyImport_ImportModule("pyfora.BinaryObjectRegistryHelpers");
    if (binaryObjectRegistryHelpersModule == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }

    mComputedValueDataStringFun = PyObject_GetAttrString(
        binaryObjectRegistryHelpersModule,
        "computedValueDataString"
        );
    
    Py_DECREF(binaryObjectRegistryHelpersModule);

    if (mComputedValueDataStringFun == NULL) {
        throw std::runtime_error(PyObjectUtils::exc_string());
        }
    }

PyObject* BinaryObjectRegistryHelpers::computedValueDataString(
       const PyObject* computedValueArg
       )
    {
    PyObject* tr = PyObject_CallFunctionObjArgs(
        _getInstance().mComputedValueDataStringFun,
        computedValueArg,
        NULL
        );

    if (tr == NULL) {
        return NULL;
        }

    if (not PyString_Check(tr)) {
        PyErr_SetString(
            PyExc_TypeError,
            "expected BinaryObjectRegistryHelpers.computedValueDataString "
            "to return a string"
            );
        return NULL;
        }

    return tr;
    }
