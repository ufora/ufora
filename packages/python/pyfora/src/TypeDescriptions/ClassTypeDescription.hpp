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
#include "../core/PyObjectPtr.hpp"

#include <vector>


class IRToPythonConverter;

class ClassTypeDescription : public TypeDescription {
public:

    ClassTypeDescription(
        int64_t sourceFileId,
        int32_t linenumber,
        PyObject* freeVariableResolutions,
        const std::vector<int64_t>& baseClassIds
        );

    virtual PyObject* transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy=false
        );

private:
    int64_t mSourceFileId;
    int32_t mLinenumber;
    PyObjectPtr mFreeVariableResolutions;
    std::vector<int64_t> mBaseClassIds;

    ClassTypeDescription(const ClassTypeDescription&) = delete;
    void operator=(const ClassTypeDescription&) = delete;
};
