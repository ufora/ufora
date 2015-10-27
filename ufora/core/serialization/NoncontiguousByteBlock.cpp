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
#include "NoncontiguousByteBlock.hpp"

#include "../lassert.hpp"

NoncontiguousByteBlock::NoncontiguousByteBlock() : 
		mTotalBytes(0)
	{
	}

NoncontiguousByteBlock::NoncontiguousByteBlock(const std::string& inString)	:
		mTotalBytes(0)
	{
	push_back(inString);
	}

void NoncontiguousByteBlock::push_back(const std::string& inString)
	{
	mHash = null();

	if (inString.size() > 1024 * 1024)
		{
		//break the string up into slices
		size_t low = 0;

		while (low < inString.size())
			{
			uword_t sliceSize = std::min<size_t>(1024 * 1024, inString.size() - low);

			std::string slice = inString.substr(low, sliceSize);

			low += 1024 * 1024;

			push_back(slice);
			}
		}
	else
		{
		mStrings.push_back(inString);

		mTotalBytes += inString.size();
		}
	}

uint32_t NoncontiguousByteBlock::totalByteCount(void) const
	{
	return mTotalBytes;
	}

uint32_t NoncontiguousByteBlock::size(void) const
	{
	return mStrings.size();
	}

std::string& NoncontiguousByteBlock::operator[](uint32_t inIndex)
	{
	lassert(inIndex < mStrings.size());

	return mStrings[inIndex];
	}

const std::string& NoncontiguousByteBlock::operator[](uint32_t inIndex) const
	{
	lassert(inIndex < mStrings.size());

	return mStrings[inIndex];
	}

std::string NoncontiguousByteBlock::toString(void) const
	{
	std::string tr;
	tr.resize(mTotalBytes);
	
	char* offset = &tr[0];
	for (auto it = mStrings.begin(); it != mStrings.end(); ++it)
		{
		memcpy(offset, &(*it)[0], it->size());
		offset += it->size();
		}
	
	return tr;
	}

void NoncontiguousByteBlock::clear(void)
	{
	mHash = null();
	mStrings.clear();
	mTotalBytes = 0;
	}

hash_type NoncontiguousByteBlock::hash() const
	{
	if (!mHash)
		mHash = hashValue(toString());

	return *mHash;
	}

void Serializer<NoncontiguousByteBlock, HashingStreamSerializer>::serialize(HashingStreamSerializer& s, const NoncontiguousByteBlock& in)
	{
	s.serialize(in.hash());
	}

void Serializer<PolymorphicSharedPtr<NoncontiguousByteBlock>, HashingStreamSerializer>::serialize(
				HashingStreamSerializer& s, 
				const PolymorphicSharedPtr<NoncontiguousByteBlock>& in
				)
	{
	if (!in)
		s.serialize(hash_type(0));
	else
		{
		s.serialize(hash_type(1));
		s.serialize(in->hash());
		}
	}

