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

#include "MemBlock.hpp"

class MemBlockAllocator {
	MemBlockAllocator(const MemBlockAllocator&); //not implemented
	MemBlockAllocator& operator=(const MemBlockAllocator& in); //not implemented
public:
	MemBlockAllocator(size_t inSlabSize);

	~MemBlockAllocator();

	//get a base pointer appropriate for passing into native FORA
	MemBlock** getMemBlockPtr();

	//free some memory
	void free(void* block);

	//allocate some memory
	void* allocate(size_t inByteCount);

	//release the memblock if not already released
	void releaseAll(void);

	size_t totalBytesReserved(void);

private:
	void ensureInitialized(void);

	//the current memory block that's on the top of the stack. This is the address that
	//getMemBlockPtr() points to
	MemBlock* mBaseMemBlock;

	//the root block in the sequence of slabs, so that we can know where to start deallocating
	//if we have to rip this down.
	MemBlock* mFirstMemBlock;

	size_t mSlabSize;
};

