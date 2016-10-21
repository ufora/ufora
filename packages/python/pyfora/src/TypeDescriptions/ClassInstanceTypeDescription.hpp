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

#include <map>
#include <stdint.h>
#include <string>

#include "TypeDescription.hpp"


class IRToPythonConverter;

class ClassInstanceTypeDescription : public TypeDescription {
public:

    ClassInstanceTypeDescription(
        int64_t classId,
        const std::map<std::string, int64_t>& mClassMembers
        );
    virtual ~ClassInstanceTypeDescription();

    virtual PyObject* transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy=false
        );

private:
    int64_t mClassId;
    std::map<std::string, int64_t> mClassMembers;

    PyObject* _convertMembers(
            IRToPythonConverter& converter,
            bool retainHomogenousListsAsNumpy
            );

};

