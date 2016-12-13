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
#include "../PyObjectUtils.hpp"
#include "UnconvertibleTypeDescription.hpp"

#include <sstream>


UnconvertibleTypeDescription::UnconvertibleTypeDescription(PyObject* stringTupleOrNone)
    {
    mStringTupleOrNone = PyObjectPtr::incremented(stringTupleOrNone);
    }


PyObject* UnconvertibleTypeDescription::transform(
        IRToPythonConverter& converter,
        bool retainHomogenousListsAsNumpy
        )
    {
    return converter.getObjectFromPath(
        mStringTupleOrNone.get()
        );
    }


std::string UnconvertibleTypeDescription::toString()
    {
    std::ostringstream oss;

    oss << "<UnconvertibleTypeDescription object at "
        << (void*) this
        << ": stringTupleOrNone="
        << PyObjectUtils::str_string(mStringTupleOrNone.get())
        << ">"
        ;

    return oss.str();
    }
