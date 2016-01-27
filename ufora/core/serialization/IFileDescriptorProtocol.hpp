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
#include "IProtocol.hpp"
#include <stdio.h>

/******************

A Protocol object that writes directly to a file descriptor. 

If 'alignment' is nonzero, writes are aligned to 'alignment' byte boundaries
and the file is padded with zeros. this allows us to write using O_DIRECT.

******************/

class IFileDescriptorProtocol : public IProtocol {
	IFileDescriptorProtocol(const IFileDescriptorProtocol& in);
	IFileDescriptorProtocol& operator=(const IFileDescriptorProtocol& in);
public:
	enum class CloseOnDestroy { True, False };

	IFileDescriptorProtocol(
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
			mBufferBytesConsumed(0),
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

	~IFileDescriptorProtocol()
		{
		if (mCloseOnDestroy == CloseOnDestroy::True)
			close(mFD);
		}

	uword_t position(void)
		{
		return mPosition;
		}

	uword_t read(uword_t inByteCount, void *inData, bool inBlock)
		{
		if (inByteCount == 0)
			return 0;

		char* dataTarget = (char*)inData;

		uword_t bytesRead = 0;

		while (inByteCount > 0)
			{
			if (mBufferBytesConsumed + inByteCount < mBufferBytesUsed)
				{
				memcpy(dataTarget, mBufPtr + mBufferBytesConsumed, inByteCount);
				mBufferBytesConsumed += inByteCount;
				mPosition += inByteCount;
				bytesRead += inByteCount;

				inByteCount = 0;
				}
			else
				{
				long bytesToFinishBuffer = mBufferBytesUsed - mBufferBytesConsumed;

				if (bytesToFinishBuffer > 0)
					{
					memcpy(dataTarget, mBufPtr + mBufferBytesConsumed, bytesToFinishBuffer);

					mBufferBytesConsumed += bytesToFinishBuffer;
					dataTarget += bytesToFinishBuffer;
					inByteCount -= bytesToFinishBuffer;
					mPosition += bytesToFinishBuffer;

					bytesRead += bytesToFinishBuffer;
					}

				if (inByteCount > 0)
					{
					refillBuffer_();

					if (mBufferBytesUsed == 0)
						return bytesRead;
					}
				}
			}

		return bytesRead;
		}

private:
	void refillBuffer_()
		{
		mBufferBytesUsed = ::read(mFD, mBufPtr, mBufferSize);
		mBufferBytesConsumed = 0;
		}

	int64_t mPosition;

	int mFD;

	CloseOnDestroy mCloseOnDestroy;

	size_t mBufferBytesUsed;

	std::vector<char> mBufferHolder;

	char* mBufPtr;

	size_t mAlignment;

	size_t mBufferSize;

	size_t mBufferBytesConsumed;
};


