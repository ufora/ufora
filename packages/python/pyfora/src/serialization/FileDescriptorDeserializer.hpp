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

#include "DeserializerBase.hpp"

#include <string>
#include <vector>


class FileDescriptorDeserializer : public Deserializer {
public:
    typedef std::vector<char>::size_type size_type;

    explicit FileDescriptorDeserializer(int filedescriptor,
                                        size_t bufferSize = 16 * 4096);

    std::string toString() const;

private:
    virtual const char* _grabBytes(size_t nBytes);

    void reserveAndShiftLeft(size_t nBytes);
    void refillBuffer(size_t nBytes);
    void adjustIfNecessary(size_t nBytes);
    void shiftLeft();
    std::string notEnoughValuesErr(
        size_t nBytes,
        const std::string& extraMsg = "") const;

    std::vector<char> mBuffer;
    size_t mReadHead;
    size_t mWriteHead;
    int mFileDescriptor;
};
