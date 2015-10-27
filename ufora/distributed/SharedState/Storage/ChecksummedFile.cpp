/***************************************************************************
   Copyright 2015 Ufora Inc.

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
#include "ChecksummedFile.hpp"

#include <cstdio>
#include <string>
#include <vector>
#include <stdexcept>

#include <boost/crc.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <boost/lexical_cast.hpp>


#include "../Common.hpp"

#include "../KeyState.hppml"
#include "../../../core/math/Nullable.hpp"

using namespace std;


namespace ChecksummedFile {
    namespace detail {

        void onWriteError(const std::string& path)
            {
            if (errno == ENOSPC)
                {
                LOG_CRITICAL << "No Space Left on Disk!";
                throw Ufora::OsError("No space left on SharedState storage device!", int(errno));
                }
            lassert_dump(false, "ChecksummedFile failed to write to " + path)
            }

        uint64_t fileSize(FILE* inFile)
            {
            uint64_t curPos = ftell(inFile);
            fseek(inFile, 0L, SEEK_END);
            uint64_t tr = ftell(inFile);
            fseek(inFile, curPos, SEEK_SET);
            return tr;
            }

        FILE* openFile(const string& fileName, const FileMode::ModeType& mode)
            {
            FILE* tr = fopen(fileName.c_str(), (mode == FileMode::READ ? "r" : "a+"));
            if (tr == nullptr)
                {
                perror("");
                throw std::logic_error("error opening file: " + fileName);
                }
            return tr;
            }
    }


ChecksummedWriter::ChecksummedWriter(string path) :
    mFile(NULL),
    mPath(path),
    mDataError(false),
    mIsDirty(false)
    {
    LOG_INFO << "Checksummed writer opening file " << mPath;

    mFile = detail::openFile(path, FileMode::APPEND);
    }

ChecksummedWriter::~ChecksummedWriter()
    {
    if(mFile != nullptr)
        {
        LOG_INFO << "Checksummed writer closing file " << mPath;
        flush();
        fclose(mFile);
        }
    }

string ChecksummedWriter::path() const
    {
    return mPath;
    }

void ChecksummedWriter::flush()
    {
    // for external flushing
    if (fflush(mFile) != 0) {
        LOG_ERROR << "Checksummed writer failed to flush file. Error:" << ferror(mFile);
        }
    mIsDirty = false;
    }

size_t ChecksummedWriter::written() const
    {
    // return number of bytes written to this file..
    return ftell(mFile);
    }

uint64_t ChecksummedWriter::fileSize() const
    {
    return detail::fileSize(const_cast<FILE*>(mFile));
    }

bool ChecksummedWriter::isDirty() const
    {
    return mIsDirty;
    }



void ChecksummedWriter::writeString(const string& str)
    {
    // write a string to disk as checksum / size / string
    lassert(!mDataError);
    uint64_t size = str.size();

    boost::crc_32_type crc;
    crc.process_bytes(str.data(), str.size());
    uint32_t checksum = crc.checksum();

    if (fwrite(&checksum, sizeof(uint32_t), 1, mFile) != 1)
        detail::onWriteError(mPath);
    if(fwrite(&size, sizeof(uint64_t), 1, mFile) != 1)
        detail::onWriteError(mPath);
    if(fwrite(str.c_str(), sizeof(char), size, mFile) != size)
        detail::onWriteError(mPath);

    mIsDirty = true;
    }



bool readString(FILE* inFile, string& outString, int64_t& remainingBytes)
    {
    // read a string from disk and verify that it matches the checksum.
    // any disk error should result in failure. Any data error should
    // result in mDataError being set to true and null should be returned.
    if(feof(inFile)) // if the file is empty upon opening it will be eof
        return false;

    uint32_t checksum;
    if(fread(&checksum, sizeof(uint32_t), 1, inFile) != 1)
        {
        LOG_ERROR << "unable to read initial hash yet not eof: " <<  endl;
        return false;
        }

    remainingBytes -= sizeof(uint32_t);
    uint64_t size;
    if(fread(&size, sizeof(uint64_t), 1, inFile) != 1)
        {
        LOG_ERROR <<  "unable to read message size from disk";
        return false;
        }

    // ideally we'd use a fixed buffer and avoid malloc here.
    remainingBytes -= sizeof(uint64_t);

    if(size > remainingBytes)
        {
        LOG_ERROR << "message was truncated: should be " <<
            size << " remaining is " << remainingBytes;
        return false;
        }

    vector<char> buff(size);
    if(fread(&buff[0], 1, size, inFile) != size)
        {
        // since we are checking the size above this should never
        // fail!
        LOG_ERROR << "unable to read entire message from disk";
        return false;
        }
    remainingBytes -= size;

    boost::crc_32_type crc;
    crc.process_bytes(&buff[0], size);
    if(crc.checksum() != checksum)
        {
        LOG_ERROR << "message didn't match it's checksum";
        return false;
        }

    outString = string(buff.begin(), buff.end());
    return true;
    }

bool readAllToVector(std::string path, vector<string>& outVector)
    {
    lassert(outVector.size() == 0);
    FILE* file = detail::openFile(path, FileMode::READ);
    int64_t remaining = detail::fileSize(file);

    bool readAgain = true;
    string result;
    while(readAgain)
        {
        bool success = readString(file, result, remaining);
        if(!success)
            {
            if(fclose(file))
                perror("");
            return false;
            }
        outVector.push_back(result);
        readAgain = success && remaining > 0;
        }
    if(fclose(file))
        perror("");
    return true;
    }

}


