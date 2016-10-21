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
#include "StringDeserializer.hpp"

#include <sstream>
#include <stdexcept>

StringDeserializer::StringDeserializer(const std::vector<char>& data)
    : mData(data),
      mIndex(0)
    {
    }


StringDeserializer::StringDeserializer(const std::string& data)
    : mData(data.begin(), data.end()),
      mIndex(0)
    {
    }


StringDeserializer::StringDeserializer(const char* data, size_t size)
    : mData(data, data + size),
      mIndex(0)
    {
    }


const char* StringDeserializer::_grabBytes(size_t nBytes)
    {
    if (mIndex + nBytes > mData.size()) {
        std::ostringstream err;
        err << "attempting to read too many bytes from string buffer! "
            << "in StringDeserializer::_grabBytes. "
            << "mIndex = " << mIndex
            << ", nBytes = " << nBytes
            << ", mData.size() = " << mData.size()
            ;

        throw std::runtime_error(err.str());
        }

    char* res = &mData[mIndex];
    mIndex += nBytes;
    return res;
    }

