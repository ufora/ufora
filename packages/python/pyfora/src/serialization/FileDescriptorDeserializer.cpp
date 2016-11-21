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
#include "FileDescriptorDeserializer.hpp"
#include "../ScopedPyThreads.hpp"

#include <cstring>
#include <cerrno>
#include <sstream>
#include <stdexcept>
#include <unistd.h>


FileDescriptorDeserializer::FileDescriptorDeserializer(
        int filedescriptor,
        size_t bufferSize        
        )
    : mReadHead(0),
      mWriteHead(0),
      mFileDescriptor(filedescriptor)
    {
    mBuffer.resize(0);
    mBuffer.reserve(bufferSize);
    }


void FileDescriptorDeserializer::refillBuffer(size_t nBytes)
    {
    ScopedPyThreads releaseTheGil;

    size_t bytes_available = mWriteHead - mReadHead;

    while (bytes_available < nBytes) {
        ssize_t bytes_read = read(mFileDescriptor,
                                  &mBuffer[mWriteHead],
                                  mBuffer.capacity() - mWriteHead);

        if (bytes_read == 0) {
            std::ostringstream err;
            err << "stream terminated unexpectedly in "
                << __PRETTY_FUNCTION__
                << "\nnBytes = " << nBytes
                << "\nbytes_available = " << bytes_available
                << "\n" << toString()
                << "\n"
                ;
            throw std::runtime_error(err.str());
            }
        else if (bytes_read < 0) {
            std::ostringstream err;
            err << "error reading from stream: "
                << strerror(errno)
                ;
            throw std::runtime_error(err.str());
            }

        bytes_available += bytes_read;
        mWriteHead += bytes_read;
        }
    }


void FileDescriptorDeserializer::shiftLeft()
    {
    memmove(&mBuffer[0], &mBuffer[mReadHead], mWriteHead - mReadHead);
    mWriteHead -= mReadHead;
    mReadHead = 0;
    }


void FileDescriptorDeserializer::reserveAndShiftLeft(size_t nBytes)
    {
    std::vector<char> newBuffer;
    newBuffer.resize(0);
    newBuffer.reserve(nBytes);

    if (mWriteHead - mReadHead > newBuffer.capacity()) {
        std::ostringstream err;
        err << "not enough space in new buffer. new buffer capacity: "
            << newBuffer.capacity()
            << ", mWriteHead - mReadHead = " << (mWriteHead - mReadHead)
            ;

        throw std::runtime_error(err.str());
        }

    memcpy(&newBuffer[0], &mBuffer[mReadHead], mWriteHead - mReadHead);

    mBuffer.swap(newBuffer);

    mWriteHead -= mReadHead;
    mReadHead = 0;
    }


std::string FileDescriptorDeserializer::notEnoughValuesErr(
        size_t nBytes,
        const std::string& extraMsg
        ) const
    {
    std::ostringstream err;
    err << "couldn't find enough values in "
        << "filedescriptor " << mFileDescriptor
        ;

    if (extraMsg.size()) {
        err << "\n" << extraMsg << "\n";
        }

    err << "\nnBytes = " << nBytes
        << "\n" << toString()
        ;

    return err.str();
    }


void FileDescriptorDeserializer::adjustIfNecessary(size_t nBytes)
    {
    if (mReadHead + nBytes <= mWriteHead) {
        return;
        }

    if (nBytes <= mBuffer.capacity())
        { // don't need to resize buffer
        if (mReadHead + nBytes >= mBuffer.capacity())
            { // need to shift the values to make space
            shiftLeft();
            }

        refillBuffer(nBytes);
        }
    else { // need to serve more space in the buffer.
        reserveAndShiftLeft(nBytes);
        refillBuffer(nBytes);
        }
    }


const char* FileDescriptorDeserializer::grabBytes(size_t nBytes)
    {
    adjustIfNecessary(nBytes);

    if (mReadHead + nBytes > mWriteHead or
        mReadHead + nBytes > mBuffer.capacity()) {
        std::ostringstream err;
        err << "not enough space in buffer to read "
            << nBytes
            << " bytes.\n"
            << toString();

        throw std::runtime_error(err.str());
        }            

    const char* tr = &mBuffer[mReadHead];
    mReadHead += nBytes;
    return tr;
    }


std::string FileDescriptorDeserializer::toString() const
    {
    std::ostringstream oss;
    oss << "<FileDescriptorDeserializer object at "
        << (void*) this
        << ": "
        << "\n\tmBuffer = " << (void*)&mBuffer[0]
        << "\n\tmReadHead = " << mReadHead
        << "\n\tmWriteHead = " << mWriteHead
        << "\n\tcapacity() = " << mBuffer.capacity()
        << "\n\tmFileDescriptor = " << mFileDescriptor
        << "\n\t>"
        ;
    return oss.str();
    }
