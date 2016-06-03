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
#include "IProtocol.hpp"

class IBinaryStream {
	IBinaryStream(const IBinaryStream& in) : mProtocol(in.mProtocol)
		{
		}
	IBinaryStream& operator=(const IBinaryStream& in)
		{
		return *this;
		}
public:
	typedef uint32_t size_type;

	IBinaryStream(IProtocol& inProtocol, size_type inBufferSize = 4096) :
			mProtocol(inProtocol), mBytesRead(0)
		{
		mBuffer.resize(0);
		mBuffer.reserve(inBufferSize);
		mBufferPos = 0;
		mBufferPreferredSize = inBufferSize;
		}

	~IBinaryStream()
		{
		}

	size_type position(void)
		{
		return mProtocol.position() - (mBuffer.size() - mBufferPos);
		}

	void read(size_type inBytes, void* inData)
		{
		mBytesRead += inBytes;

		while (inBytes > 0)
			{
			int32_t avail = inBytes;
			if (avail + mBufferPos > mBuffer.size())
				avail = mBuffer.size() - mBufferPos;

			if (avail != 0)
				memcpy(inData, &mBuffer[mBufferPos], avail);

			mBufferPos += avail;
			inData = (char*)inData + avail;
			inBytes -= avail;

			if (inBytes == 0)
				return;

			// We still have data left to read. We will either read directly through the protocol
			// or fill up a buffer.
			if (inBytes > mBufferPreferredSize)
				{
				uint32_t bytesRead = mProtocol.read(inBytes, inData, true);
				inBytes -= bytesRead;
				inData = (char*)inData + bytesRead;

				clearBuffer();
				}
			else
				refillBuffer(inBytes);
			}
		}

	void clearBuffer(void)
		{
		mBufferPos = 0;
		mBuffer.resize(0);
		}

	void refillBuffer(size_type minBytes)
		{
		lassert(minBytes >= 0);
		lassert(mBufferPos >= mBuffer.size());
		lassert(minBytes <= mBufferPreferredSize);

		clearBuffer();

		mBuffer.resize(mBufferPreferredSize);
		size_type bytesRead = mProtocol.read(mBufferPreferredSize, &mBuffer[0], false);

		if (bytesRead >= minBytes)
			{
			//we read enough - just return
			mBuffer.resize(bytesRead);
			}
		else
			{
			//force read to block until minimum number of bytes have been read
			bytesRead += mProtocol.read(minBytes - bytesRead, &mBuffer[bytesRead], true);
			mBuffer.resize(bytesRead);
			}

		lassert_dump(bytesRead >= minBytes, "Needed to get " << minBytes << " but only got "
					<< bytesRead);
		}

	size_type bytesRead() const
		{
		return mBytesRead;
		}

private:
	IProtocol& 			mProtocol;
	std::vector<char> 	mBuffer;
	size_type 			mBufferPos;
	size_type			mBufferPreferredSize;
	size_type 			mBytesRead;
}; // IBinaryStream


