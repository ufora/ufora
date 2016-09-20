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


void StringBuilder::addByte(char b) {
    _add(b);
    }


void StringBuilder::addInt32(int32_t i) {
    _add(i);
    }


void StringBuilder::addInt64(int64_t i) {
    _add(i);
    }
        

void StringBuilder::addInt64s(const std::vector<int64_t>& integers) {
    addInt64s(reinterpret_cast<const int64_t*>(&integers[0]), integers.size());
    }


void StringBuilder::addInt64s(const int64_t* integers, uint64_t nIntegers) {
    addInt64(nIntegers);
    _write(reinterpret_cast<const char*>(integers), nIntegers * sizeof(int64_t));
    }


void StringBuilder::addFloat64(double f) {
    _add(f);
    }


void StringBuilder::addString(const std::string& s) {
    addString(s.data(), s.size());
    }


void StringBuilder::addString(const char* s, uint64_t byteCount) {
    addInt32(byteCount);
    _write(s, byteCount);
   }


void StringBuilder::addStrings(const std::vector<std::string>& strings) {
    addInt32(strings.size());
    for (std::vector<std::string>::const_iterator it = strings.begin();
         it != strings.end();
         ++it)
        addString(*it);
    }


void StringBuilder::_write(const char* data, uint64_t byteCount) {
    mStream.write(data, byteCount);
    mByteCount += byteCount;
    }


void StringBuilder::addStringTuple(const std::string& s) {
    addInt32(s.size());
    for (uint64_t ix = 0; ix < s.size(); ++ix)
        addString(std::string(1, s[ix]));
    }
        

void StringBuilder::addStringTuple(const char* s, uint64_t byteCount) {
    addInt32(byteCount);
    for (uint64_t ix = 0; ix < byteCount; ++ix)
        addString(std::string(1, s[ix]));
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
