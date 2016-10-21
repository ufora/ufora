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
#include <string>
#include <vector>


class Deserializer {
public:
    virtual ~Deserializer()
        {
        }

    char readByte();
    int32_t readInt32();
    int64_t readInt64();
    double readFloat64();
    void readInt64s(std::vector<int64_t>& ioInts);
    std::string readString();

private:
    /*
      return a pointer to an internal buffer
      which *must* be valid for at least nBytes.

      This is a stateful call -- internal data structures
      should be advanced to provide new bytes on secondary
      calls.

      This call must also not touch any Python data structures,
      or python API calls
    */
    const char* grabBytes(size_t nBytes);

    // actual implementation of grabBytes, with the 
    // work being done after releasing the Python GIL
    virtual const char* _grabBytes(size_t nBytes) = 0;

};

/*
  We're assuming we're on an architecture which supports unaligned reads,
  such as x86
 */

inline
int32_t Deserializer::readInt32() {
    return *(reinterpret_cast<const int32_t*>(grabBytes(sizeof(int32_t))));
    }


inline
int64_t Deserializer::readInt64() {
    return *(reinterpret_cast<const int64_t*>(grabBytes(sizeof(int64_t))));
    }


inline
double Deserializer::readFloat64() {
    return *(reinterpret_cast<const double*>(grabBytes(sizeof(double))));
    }


inline
std::string Deserializer::readString() {
    int64_t count = readInt32();
    return  std::string(grabBytes(count), count);
    }


inline
char Deserializer::readByte()
    {
    return *grabBytes(1);
    }


