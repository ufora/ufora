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
#include "../IRToPythonConverter.hpp"
#include "UnresolvedSymbolTypeDescription.hpp"

#include <sstream>


UnresolvedSymbolTypeDescription::UnresolvedSymbolTypeDescription(
        const std::string& varname,
        int64_t linenumber,
        int64_t col_offset
        )
    : mVarname(varname),
      mLineNumber(linenumber),
      mColumnOffset(col_offset)
    {
    }


PyObject* UnresolvedSymbolTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    PyObjectPtr exceptionsModule = PyObjectPtr::unincremented(
        PyImport_ImportModule("pyfora.Exceptions")
        );
    if (exceptionsModule == nullptr) {
        return nullptr;
        }
    PyObjectPtr pyforaNameErrorClass = PyObjectPtr::unincremented(
        PyObject_GetAttrString(
            exceptionsModule.get(),
            "PyforaNameError"
            )
        );
    if (pyforaNameErrorClass == nullptr) {
        return nullptr;
        }
    
    std::string errString = std::string("global name '") +
        mVarname + "' is not defined";
    
    PyObjectPtr pyErrString = PyObjectPtr::unincremented(
        PyString_FromStringAndSize(
            errString.data(),
            errString.size()
            )
        );
    if (pyErrString == nullptr) {
        return nullptr;
        }

    return PyObject_Call(
        pyforaNameErrorClass.get(),
        pyErrString.get(),
        nullptr);
    }


std::string UnresolvedSymbolTypeDescription::toString()
    {
    std::ostringstream oss;

    oss << "<UnresolvedSymbolTypeDescription object at "
        << (void*) this
        << "varname=" << mVarname
        << ", lineno=" << mLineNumber
        << ", col_offset=" << mColumnOffset
        << ">"
        ;

    return oss.str();
    }
