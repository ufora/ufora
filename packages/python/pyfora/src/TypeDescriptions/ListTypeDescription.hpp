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

#include <vector>

#include "TypeDescription.hpp"


class IRToPythonConverter;

class ListTypeDescription : public TypeDescription {
public:

    explicit ListTypeDescription(const std::vector<int64_t>& memberIds);
    virtual ~ListTypeDescription();

    virtual PyObject* transform(
        IRToPythonConverter& c,
        bool retainHomogenousListsAsNumpy=false
        );

private:
    std::vector<int64_t> mMemberIds;
};

