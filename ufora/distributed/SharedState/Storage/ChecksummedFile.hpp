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
#pragma once

#include <string>
#include <vector>
#include <boost/enable_shared_from_this.hpp>



/*
This file contains tools that allow checksummed file IO.
The desired pattern is one where a user wants to hold an open file for
appending and then perodically read the entire contents at once.
*/

namespace ChecksummedFile {
	namespace FileMode {
		enum ModeType {READ = 0, APPEND = 1};
	}

	namespace detail {
		uint64_t fileSize(FILE* inFile);
		FILE*  openFile(const std::string& fileName, const FileMode::ModeType& mode);
	}
	
	class ChecksummedWriter : public boost::enable_shared_from_this<ChecksummedWriter> {
	public:
			explicit ChecksummedWriter(std::string path);

			~ChecksummedWriter();

			std::string path() const;

			void flush();

			size_t written() const;

			uint64_t fileSize() const;

			void writeString(const std::string& str);
			
			bool isDirty() const;

	private:
			// obviously we don't want this to be copied
			ChecksummedWriter(const ChecksummedWriter& other);

			ChecksummedWriter& operator=(const ChecksummedWriter& other);

			FILE* 					mFile;
			std::string				mPath;
			bool					mDataError;
			bool					mIsDirty;
	};
	

	bool readString(FILE* inFile, std::string& outString, int64_t& remainingBytes);

	bool readAllToVector(std::string path, std::vector<std::string>& outVector);


} // ChecksummedFile namespace



