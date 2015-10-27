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
#include "MemBlockAllocator.hpp"

#include "../../core/lassert.hpp"

MemBlockAllocator::MemBlockAllocator(size_t inSlabSize) : 
		mSlabSize(inSlabSize),
		mBaseMemBlock(0),
		mFirstMemBlock(0)
	{
	}

MemBlockAllocator::~MemBlockAllocator()
	{
	releaseAll();
	}

//get a base pointer appropriate for passing into native FORA
MemBlock** MemBlockAllocator::getMemBlockPtr()
	{
	ensureInitialized();

	return &mBaseMemBlock;
	}

//free some memory
void MemBlockAllocator::free(void* block)
	{
	lassert_dump(mFirstMemBlock, "MemBlockAllocator is empty");

	FORA_clib_freeMem(&mBaseMemBlock, block);
	}

//allocate some memory
void* MemBlockAllocator::allocate(size_t inByteCount)
	{
	ensureInitialized();

	return FORA_clib_allocMem(&mBaseMemBlock, inByteCount);
	}

//release the memblock if not already released
void MemBlockAllocator::releaseAll(void)
	{
	if (mFirstMemBlock)
		{
		FORA_clib_freeSlab(mFirstMemBlock->rootSlab);
		mFirstMemBlock = 0;
		mBaseMemBlock = 0;
		}
	}

void MemBlockAllocator::ensureInitialized(void)
	{
	if (!mBaseMemBlock)
		{
		MemSlab* slab = FORA_clib_allocNewEmptySlab(mSlabSize);
		mBaseMemBlock = &slab->baseBlock;
		mFirstMemBlock = mBaseMemBlock;
		}
	}

size_t MemBlockAllocator::totalBytesReserved(void)
	{
	if (!mBaseMemBlock)
		return 0;
	
	size_t tr = 0;

	MemSlab* slab = mFirstMemBlock->rootSlab;
	while (slab)
		{
		tr = tr + slab->used();
		slab = slab->nextSlab;
		}

	return tr;
	}

