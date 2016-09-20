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

#include <stdint.h>
#include <string>
#include <vector>


class StringDeserializer {
public:
    StringDeserializer(const std::vector<char>& data);

    bool finished() {
        return mIndex >= mData.size();
        }

    char readByte();
    int32_t readInt32();
    int64_t readInt64();
    double readFloat64();
    void readInt64s(std::vector<int64_t>& ioInts);
    std::string readString();

private:
    std::vector<char> mData;
    uint64_t mIndex;
    };
