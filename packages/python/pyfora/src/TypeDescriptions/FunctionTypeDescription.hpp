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


class IRToPythonConverter;

class FunctionTypeDescription : public TypeDescription {
public:

    FunctionTypeDescription(
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions
        );
    virtual ~FunctionTypeDescription();

    virtual PyObject* transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy=false
        );

private:
    int64_t mSourceFileId;
    int32_t mLinenumber;
    PyObject* mFreeVariableResolutions;

    FunctionTypeDescription(const FunctionTypeDescription&) = delete;
    void operator=(const FunctionTypeDescription&) = delete;
};
