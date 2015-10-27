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
#include "SimpleMemoryAllocator.hpp"

SimpleMemoryAllocator::SimpleMemoryAllocator(uword_t totalSize, uword_t inAlignment) : 
		mAlignment(inAlignment),
		mTotalSize(totalSize)
	{
	lassert_dump(totalSize % mAlignment == 0, 
			"memory size must be " << mAlignment << "-byte aligned");

	mOffsetToBlocksizeMapUnallocated.insert(0, totalSize);
	mUnallocatedBlockUpperBoundsToOffsets[totalSize] = 0;
	}

uword_t SimpleMemoryAllocator::allocate(uword_t inSize)
	{
	if (inSize == 0)
		return mTotalSize;

	//round inSize up to 8 byte alignment
	if (inSize % mAlignment != 0)
		inSize = inSize + (mAlignment - inSize % mAlignment);

	//find an unallocated block that's big enough to hold this one
	auto it = mOffsetToBlocksizeMapUnallocated.getValueToKeys().lower_bound(inSize);

	if (it == mOffsetToBlocksizeMapUnallocated.getValueToKeys().end())
		throw std::bad_alloc();

	uword_t blockSize = it->first;
	uword_t blockOffset = *it->second.begin();

	mOffsetToBlocksizeMapUnallocated.drop(blockOffset);

	//now, decide if we need the whole block
	if (inSize < blockSize)
		{
		//we're splitting the block
		mOffsetToBlocksizeMapUnallocated.insert(blockOffset + inSize, blockSize - inSize);

		//update its top-range
		mUnallocatedBlockUpperBoundsToOffsets[blockOffset + blockSize] = blockOffset + inSize;
		}
	else
		{
		//we're going to use the whole block
		mUnallocatedBlockUpperBoundsToOffsets.erase(blockOffset + inSize);
		}

	mOffsetToBlocksizeMapAllocated.insert(blockOffset, inSize);

	return blockOffset;
	}

void SimpleMemoryAllocator::freeAtOffset(uword_t blockOffset)
	{
	if (blockOffset == mTotalSize)
		return;

	lassert(mOffsetToBlocksizeMapAllocated.hasKey(blockOffset));

	uword_t bytesAllocated = mOffsetToBlocksizeMapAllocated.getValue(blockOffset);

	//deallocate the block
	mOffsetToBlocksizeMapAllocated.drop(blockOffset);

	//check if the block above us is deallocated, and if so, glom it onto us
	if (mOffsetToBlocksizeMapUnallocated.hasKey(blockOffset + bytesAllocated))
		{
		uword_t sizeOfBlockToGlom = 
			mOffsetToBlocksizeMapUnallocated.getValue(blockOffset + bytesAllocated);

		//drop the deallocated block
		mOffsetToBlocksizeMapUnallocated.drop(blockOffset + bytesAllocated);
		mUnallocatedBlockUpperBoundsToOffsets.erase(blockOffset + bytesAllocated + sizeOfBlockToGlom);

		//increase the size of our block
		bytesAllocated += sizeOfBlockToGlom;
		}

	//now check if our bottom-end range is the top-end of a deallocated block
	if (mUnallocatedBlockUpperBoundsToOffsets.find(blockOffset) != 
				mUnallocatedBlockUpperBoundsToOffsets.end())
		{
		uword_t newOffset = mUnallocatedBlockUpperBoundsToOffsets[blockOffset];
		
		mUnallocatedBlockUpperBoundsToOffsets.erase(blockOffset);

		mOffsetToBlocksizeMapUnallocated.drop(newOffset);

		//expand the size of our block
		bytesAllocated += blockOffset - newOffset;
		blockOffset = newOffset;
		}

	mOffsetToBlocksizeMapUnallocated.insert(blockOffset, bytesAllocated);
	mUnallocatedBlockUpperBoundsToOffsets[blockOffset + bytesAllocated] = blockOffset;
	}

uword_t SimpleMemoryAllocator::maxAllocatableBlockSize(void)
	{
	if (!mOffsetToBlocksizeMapUnallocated.size())
		return 0;
	return mOffsetToBlocksizeMapUnallocated.highestValue();
	}
	

void SimpleMemoryAllocator::checkInternalConsistency(void)
	{
	const std::map<uword_t, uword_t>& allocatedBlockSizes(mOffsetToBlocksizeMapAllocated.getKeyToValue());
	const std::map<uword_t, uword_t>& unallocatedBlockSizes(mOffsetToBlocksizeMapUnallocated.getKeyToValue());

	uword_t totalBytesAllocated = 0;
	uword_t totalBytesUnallocated = 0;
	
	//loop over all pairs of allocated blocks
	for (auto it = allocatedBlockSizes.begin(); it != allocatedBlockSizes.end(); ++it)
		{
		totalBytesAllocated += it->second;

		auto it2 = it;
		it2++;
		if (it2 != allocatedBlockSizes.end())
			{
			lassert_dump(it->first + it->second <= it2->first, "allocated blocks overlapped");
			if (it->first + it->second < it2->first)
				{
				//verify that the unallocated blocks make sense
				lassert_dump(mOffsetToBlocksizeMapUnallocated.hasKey(it->first + it->second),
					"unallocated block was missing");

				lassert_dump(mOffsetToBlocksizeMapUnallocated.getValue(it->first + it->second) == 
					it2->first - (it->first + it->second),
					"unallocated block had incorrect size");
				}
			}
		}

	//now loop over all pairs of unallocated blocks and check their consistency
	for (auto it = unallocatedBlockSizes.begin(); it != unallocatedBlockSizes.end(); ++it)
		{
		totalBytesUnallocated += it->second;

		auto it2 = it;
		it2++;

		if (it2 != unallocatedBlockSizes.end())
			{
			//unallocated blocks shouldn't overlap or even touch
			lassert_dump(it->first + it->second < it2->first, "unallocated blocks overlapped");

			//verify that there are allocated blocks in between
			lassert_dump(
				mOffsetToBlocksizeMapAllocated.hasKey(it->first + it->second) || 
				it->first + it->second == mTotalSize,
				"top end of unallocated block wasn't an allocated block."
				);

			//verify that the upper-bound map has the entry
			lassert_dump(
				mUnallocatedBlockUpperBoundsToOffsets.find(it->first + it->second) != 
					mUnallocatedBlockUpperBoundsToOffsets.end(),
				"upper bound map doesn't have an entry at " << (it->first + it->second)
				);

			lassert_dump(
				mUnallocatedBlockUpperBoundsToOffsets[it->first + it->second] == it->first,
				"upper bound map corrupt: we have an entry at " << (it->first + it->second)
					<< " that points at " 
					<< mUnallocatedBlockUpperBoundsToOffsets[it->first + it->second] 
					<< " instead of " << it->first

				);
			}
		}

	lassert_dump(totalBytesAllocated + totalBytesUnallocated == mTotalSize, 
		"sizes of allocated/deallocated regions didn't add up to total size: " << 
			totalBytesAllocated << " + " << totalBytesUnallocated << " != " << mTotalSize
		);
	}



