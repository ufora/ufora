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

#include <vector>
#include "../lassert.hpp"
#include "Common.hpp"
#include "OProtocol.hpp"

class OBinaryStream {
	OBinaryStream(const OBinaryStream& in) : mProtocol(in.mProtocol)
		{
		}
	OBinaryStream& operator=(const OBinaryStream& in)
		{
		return *this;
		}

public:
	typedef uint32_t size_type;

	OBinaryStream(OProtocol& inProtocol, size_type inBufferSize = 4096 * 16)
			: mProtocol(inProtocol), mBytesWritten(0)
		{
		mBuffer.resize(inBufferSize);
		mBufferPos = 0;
		}
	~OBinaryStream()
		{
		flush();
		}
	size_type	position(void)
		{
		return mBufferPos + mProtocol.position();
		}

	void flush(void)
		{
		mProtocol.write(mBufferPos, &mBuffer[0]);
		mBufferPos = 0;
		}
	void write(size_type inBytes, const void* inData)
		{
		mBytesWritten += inBytes;

		if (inBytes == 0)
			return;
		if (inBytes + mBufferPos > mBuffer.size())
			{
			flush();
			mProtocol.write(inBytes, inData);
			return;
			}
		memcpy(&mBuffer[mBufferPos], inData, inBytes);

		mBufferPos += inBytes;
		}

	size_type bytesWritten() const
		{
		return mBytesWritten;
		}

private:
	OProtocol& 			mProtocol;
	std::vector<char> 	mBuffer;
	size_type 			mBufferPos;
	size_type 			mBytesWritten;
}; // OBinaryStream




