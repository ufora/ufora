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
#include "IMemProtocol.hpp"

IMemProtocol::IMemProtocol(const char* inData, 
						uword_t inSize, 
						uword_t inPosition
						) : 
		mData(inData)
	{
	lassert(inPosition <= inSize);
	mPosition = inPosition;
	mDataSize = inSize;
	}

IMemProtocol::IMemProtocol(const std::string& inData, uword_t inPosition) : 
		mData(&inData[0])
	{
	lassert(inPosition <= inData.size());
	mPosition = inPosition;
	mDataSize = inData.size();
	}

IMemProtocol::IMemProtocol(const std::vector<char>& inData, uword_t inPosition) : 
		mData(&inData[0])
	{
	lassert(inPosition <= inData.size());
	mPosition = inPosition;
	mDataSize = inData.size();
	}

uword_t IMemProtocol::read(uword_t inByteCount, void *inData, bool inBlock)
	{
	uword_t bytesAvailable = mDataSize - mPosition;

	if (inByteCount > bytesAvailable)
		inByteCount = bytesAvailable;

	memcpy(inData, &mData[mPosition], inByteCount);

	mPosition += inByteCount;

	return inByteCount;
	}

void IMemProtocol::reset(const char* inData, uword_t inSize, uword_t inPosition)
	{
	mData = inData;
	mPosition = inPosition;
	mDataSize = inSize;
	}

void IMemProtocol::reset(const std::string& inData, uword_t inPosition)
	{
	mData = &inData[0];
	mPosition = inPosition;
	mDataSize = inData.size();
	}

void IMemProtocol::reset(const std::vector<char>& inData, uword_t inPosition)
	{
	mData = &inData[0];
	mPosition = inPosition;
	mDataSize = inData.size();
	}

uword_t IMemProtocol::position(void)
	{
	return mPosition;
	}

