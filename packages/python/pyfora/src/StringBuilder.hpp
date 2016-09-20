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

#include <stdint.h>
#include <sstream>
#include <string>
#include <vector>


class StringBuilder {
public:
    StringBuilder();
    
    void addByte(char b);
    void addInt32(int32_t i);
    void addInt64(int64_t i);
    void addFloat64(double f);

    void addInt64s(const std::vector<int64_t>& integers);
    void addInt64s(const int64_t* integers, uint64_t nIntegers);
    void addString(const std::string& s);
    void addString(const char* s, uint64_t byteCount);
    void addStrings(const std::vector<std::string>& strings);
    void addStringTuple(const std::string& s);
    void addStringTuple(const char* s, uint64_t byteCount);
    void addStringTuple(const PyObject* tupOfStrings);

    std::string str() const  {
        return mStream.str();
        }

    uint64_t bytecount() const {
        return mByteCount;
        }

    void clear() {
        mStream.clear();
        mStream.str("");
        mByteCount = 0;
        }

private:
    template<typename T>
    void _add(T t) {
        _write(reinterpret_cast<const char*>(&t), sizeof(t));
        }

    void _write(const char* data, uint64_t byteCount);

    std::ostringstream mStream;
    uint64_t mByteCount;
    };
