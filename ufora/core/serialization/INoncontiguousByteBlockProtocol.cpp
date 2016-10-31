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
#include "INoncontiguousByteBlockProtocol.hpp"

INoncontiguousByteBlockProtocol::INoncontiguousByteBlockProtocol(
						PolymorphicSharedPtr<NoncontiguousByteBlock> inData
						) :
		mData(inData),
		mCurrentVectorIx(0),
		mByteOffsetWithinCurrentVector(0),
		mBytesRemaining(mData->totalByteCount()),
		mPosition(0)
	{
	}

uword_t INoncontiguousByteBlockProtocol::read(uword_t inByteCount, void *inData, bool inBlock)
	{
	if (inByteCount > mBytesRemaining)
		inByteCount = mBytesRemaining;

	uword_t totalRead = 0;

	while (inByteCount > 0)
		{
		uword_t bytesLeftInCurrentVector =
			(*mData)[mCurrentVectorIx].size() - mByteOffsetWithinCurrentVector;

		char* baseAddrWithinCurrentVector =
			&(*mData)[mCurrentVectorIx][mByteOffsetWithinCurrentVector];

		if (inByteCount < bytesLeftInCurrentVector)
			{
			//chunk is contained in this vector
			memcpy(inData, baseAddrWithinCurrentVector, inByteCount);

			mByteOffsetWithinCurrentVector += inByteCount;
			mBytesRemaining -= inByteCount;
			mPosition += inByteCount;
			totalRead += inByteCount;

			return totalRead;
			}
		else
			{
			//chunk is not entirely contained
			memcpy(
				inData,
				baseAddrWithinCurrentVector,
				bytesLeftInCurrentVector
				);

			inByteCount -= bytesLeftInCurrentVector;

			mBytesRemaining -= bytesLeftInCurrentVector;
			mPosition += bytesLeftInCurrentVector;
			totalRead += bytesLeftInCurrentVector;

			inData = reinterpret_cast<void*>(
				reinterpret_cast<char*>(inData) + bytesLeftInCurrentVector
				);

			mCurrentVectorIx++;
			mByteOffsetWithinCurrentVector = 0;
			}
		}

	return totalRead;
	}

uword_t INoncontiguousByteBlockProtocol::position(void)
	{
	return mPosition;
	}

