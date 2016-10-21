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
#include "StringBuilder.hpp"

#include <stdexcept>


StringBuilder::StringBuilder() : mByteCount(0)
    {
    }


void StringBuilder::addStringTuple(const PyObject* tupOfStrings) {
    if (not PyTuple_Check(tupOfStrings)) {
        throw std::runtime_error("addStringTuple needs tuple arguments");
        }
    
    Py_ssize_t len = PyTuple_GET_SIZE(tupOfStrings);
    
    addInt32(len);

    for (Py_ssize_t ix = 0; ix < len; ++ix) {
        PyObject* item = PyTuple_GET_ITEM(tupOfStrings, ix);
        if (not PyString_Check(item)) {
            throw std::runtime_error("addStringTuple needs to be a tuple of *strings*");
            }
        addString(PyString_AS_STRING(item), PyString_GET_SIZE(item));
        }
    }
