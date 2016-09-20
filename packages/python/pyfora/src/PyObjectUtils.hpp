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


class PyObjectUtils {
public:
    static std::string repr_string(PyObject* obj);
    static std::string str_string(PyObject* obj);

    // string should be a PyString, or PyUnicode object.
    static std::string std_string(PyObject* string);

    static std::string format_exc();

    static std::string exc_string();

    static long builtin_id(PyObject*);

    static bool in(PyObject* container, PyObject* value);

private:
    // no checking is done on pyList arg -- it must be a non-null
    // PyList*
    static bool _in_list(PyObject* pyList, PyObject* value);

};
