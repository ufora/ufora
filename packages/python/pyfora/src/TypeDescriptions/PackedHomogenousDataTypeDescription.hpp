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
#pragma once

#include <Python.h>

#include "TypeDescription.hpp"

#include <string>


class IRToPythonConverter;

class PackedHomogenousDataTypeDescription 
    : public TypeDescription {
public:

    // we're going to wind up copying all this data!
    // is that a problem?
    PackedHomogenousDataTypeDescription(
        PyObject* dtype,
        const std::string& packedBytes
        );
    virtual ~PackedHomogenousDataTypeDescription();

    virtual PyObject* transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy=false
        );

private:
    PyObject* mDtype;
    std::string mPackedBytes;

    PackedHomogenousDataTypeDescription(
        const PackedHomogenousDataTypeDescription&
        ) = delete;
    void operator=(const PackedHomogenousDataTypeDescription&) = delete;
};
