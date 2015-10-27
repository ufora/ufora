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
#include <deque>
#include "../Common.hppml"
#include "../Logging.hpp"
#include "OProtocol.hpp"
#include <stdio.h>

/******************

A Protocol object that writes directly to a file descriptor. 

If 'alignment' is nonzero, writes are aligned to 'alignment' byte boundaries
and the file is padded with zeros. this allows us to write using O_DIRECT.

******************/

class OFileDescriptorProtocol : public OProtocol {
	OFileDescriptorProtocol(const OFileDescriptorProtocol& in);
	OFileDescriptorProtocol& operator=(const OFileDescriptorProtocol& in);
public:
	enum class CloseOnDestroy { True, False };

	OFileDescriptorProtocol(
				int fd, 
				size_t alignment, 
				size_t bufsize, 
				CloseOnDestroy closeOnDestroy = CloseOnDestroy::False
				) :
			mFD(fd),
			mPosition(0),
			mCloseOnDestroy(closeOnDestroy),
			mAlignment(alignment),
			mBufferSize(bufsize),
			mBufferBytesUsed(0),
			mBufPtr(0)
		{
		lassert(mBufferSize % mAlignment == 0);

		mBufferHolder.resize(mAlignment * 2 + mBufferSize);
		uword_t bufptr = (uword_t)&mBufferHolder[0];
		
		//make sure that the buffer is aligned to the alignment as well
		if (bufptr % mAlignment)
			bufptr += mAlignment - bufptr % mAlignment;

		mBufPtr = (char*)bufptr;
		}

	~OFileDescriptorProtocol()
		{
		if (mBufferBytesUsed)
			{
			lassert(mAlignment > 0);

			if (mBufferBytesUsed % mAlignment)
				{
				memset(mBufPtr + mBufferBytesUsed, 0, mAlignment - mBufferBytesUsed % mAlignment);

				mBufferBytesUsed += mAlignment - mBufferBytesUsed % mAlignment;
				}

			try {
				write_(mBufferBytesUsed, mBufPtr);
				}
			catch(std::logic_error& e)
				{
				LOG_CRITICAL << "Exception thrown while flushing an OFileDescriptorProtocol:\n"
					<< e.what();
				}
			catch(...)
				{
				LOG_CRITICAL << "Unknown exception thrown while flushing an OFileDescriptorProtocol\n";
				}
			}

		if (mCloseOnDestroy == CloseOnDestroy::True)
			close(mFD);
		}

	uword_t position(void)
		{
		return mPosition;
		}

	void write(uword_t inByteCount, void *inData)
		{
		if (inByteCount == 0)
			return;

		mPosition += inByteCount;

		while (inByteCount)
			{
			if (mBufferBytesUsed + inByteCount < mBufferSize)
				{
				memcpy(mBufPtr + mBufferBytesUsed, inData, inByteCount);
				mBufferBytesUsed += inByteCount;
				inByteCount = 0;
				}
			else
				{
				long bytesToFinishBuffer = mBufferSize - mBufferBytesUsed;

				memcpy(mBufPtr + mBufferBytesUsed, inData, bytesToFinishBuffer);

				write_(mBufferSize, mBufPtr);

				mBufferBytesUsed = 0;

				inByteCount -= bytesToFinishBuffer;

				inData = (char*)inData + bytesToFinishBuffer;
				}
			}
		}

private:
	void write_(uword_t inByteCount, void *inData)
		{
		uint8_t* toWrite = (uint8_t*)inData;

		while (inByteCount > 0)
			{
			auto written = ::write(mFD, toWrite, inByteCount);

			if (written == -1 || written == 0)
				{
				std::string err = strerror(errno);
				lassert_dump(false, "failed to write: " << err << ". tried to write " << inByteCount);
				}

			inByteCount -= written;
			toWrite += written;
			}
		}

	int64_t mPosition;

	int mFD;

	CloseOnDestroy mCloseOnDestroy;

	size_t mBufferBytesUsed;

	std::vector<char> mBufferHolder;

	char* mBufPtr;

	size_t mAlignment;

	size_t mBufferSize;
};


