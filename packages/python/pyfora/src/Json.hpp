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

#include <string>


class Json {
public:
    static std::string dumps(const PyObject* obj);
    static PyObject* loads(const std::string& s);

private:
    // singleton instance
    static Json& _getInstance() {
        static Json instance;
        return instance;
        }

    // implement, but keep private for singleton pattern
    Json();

    // don't implement these next two for singleton pattern
    Json(const Json&) = delete;
    void operator=(const Json&) = delete;

    PyObject* mJsonModule;
};
