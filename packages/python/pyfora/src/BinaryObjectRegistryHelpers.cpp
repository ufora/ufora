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


BinaryObjectRegistryHelpers::BinaryObjectRegistryHelpers()
    {
    PyObjectPtr binaryObjectRegistryHelpersModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.BinaryObjectRegistryHelpers")
        );
    if (binaryObjectRegistryHelpersModule == nullptr) {
        throw std::runtime_error(
            "py error getting pyfora.BinaryObjectRegistryHelpers "
            "in BinaryObjectRegistryHelpers::BinaryObjectRegistryHelpers: " +
            PyObjectUtils::exc_string());
        }

    mComputedValueDataStringFun = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            binaryObjectRegistryHelpersModule.get(),
            "computedValueDataString"
            )
        );
    
    if (mComputedValueDataStringFun == nullptr) {
        throw std::runtime_error(
            "py error getting computedValueDataString in "
            "BinaryObjectRegistryHelpers::BinaryObjectRegistryHelpers: " +
            PyObjectUtils::exc_string()
            );
        }
    }


PyObject* BinaryObjectRegistryHelpers::computedValueDataString(
       const PyObject* computedValueArg
       ) const
    {
    PyObject* tr = PyObject_CallFunctionObjArgs(
        mComputedValueDataStringFun.get(),
        computedValueArg,
        nullptr
        );

    if (tr == nullptr) {
        return nullptr;
        }

    if (not PyString_Check(tr)) {
        PyErr_SetString(
            PyExc_TypeError,
            "expected BinaryObjectRegistryHelpers.computedValueDataString "
            "to return a string"
            );
        return nullptr;
        }

    return tr;
    }
