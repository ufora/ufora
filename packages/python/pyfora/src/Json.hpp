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

#include "core/PyObjectPtr.hpp"

#include <string>


class Json {
public:
    Json();

    std::string dumps(const PyObject* obj);
    PyObject* loads(const std::string& s);

private:
    void operator=(const Json&) = delete;

    PyObjectPtr mJsonModule;
};
