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
#include "MemBlock.hpp"
#include "../../core/lassert.hpp"
#include "../../core/Memory.hpp"

namespace {
uword_t gTotalSlabsAllocated = 0;
}


//statistics and a check of validity of the pointer chain
uword_t	MemSlab::used(void)
	{
	uword_t tr = 0;

	MemBlock* b = &baseBlock;

	lassert(b->prevBlock == 0);
	while (b->nextBlock)
		{
		lassert(b->nextBlock->prevBlock == b);
		tr += b->blockSize;
		b = b->nextBlock;
		}
	lassert(b == topBlock);
	lassert(b->nextBlock == 0);

	return tr;
	}

void	MemSlab::validate(void)
	{
	using namespace std;

	MemBlock* b = &baseBlock;

	lassert(b->prevBlock == 0);
	uword_t blockIx = 0;

	while (b->nextBlock)
		{
		lassert_dump(b->nextBlock >= &baseBlock && b->nextBlock <= topBlock, "block found with out-of-bounds next block!"
				<< "\n\tblock " << blockIx << " " << hex << (uword_t)b << dec << " at offset " << (uword_t)((unsigned char*)b - (unsigned char*)&baseBlock) << " with size " << b->blockSize
				<< " next = " << hex << (uword_t)b->nextBlock << " and prev = " << (uword_t)b->prevBlock << dec
				);
		lassert_dump(b->rootSlab == this, "block found with bad slab!"
				<< "\n\tblock " << blockIx << " " << hex << (uword_t)b << dec << " at offset " << (uword_t)((unsigned char*)b - (unsigned char*)&baseBlock) << " with size " << b->blockSize
				<< " next = " << hex << (uword_t)b->nextBlock << " and prev = " << (uword_t)b->prevBlock << dec
				);
		lassert_dump(b->nextBlock->prevBlock == b, "block " << blockIx << " has nextBlock at "
			<< (uword_t)((unsigned char*)b->nextBlock - (unsigned char*)&baseBlock) << ", which has size "
			<< b->nextBlock->blockSize << ", but that block has 'prevBlock' at offset "
			<< (uword_t)((unsigned char*)b->nextBlock->prevBlock - (unsigned char*)&baseBlock)
			);
		b = b->nextBlock;
		blockIx++;
		}
	lassert(b == topBlock);
	lassert(b->nextBlock == 0);
	}

extern "C" {

BSA_DLLEXPORT
MemSlab* FORA_clib_allocNewEmptySlab(uword_t maxBytes)
	{
	MemSlab* slab = (MemSlab*)Ufora::Memory::bsa_malloc(maxBytes + sizeof(MemSlab) + sizeof(MemBlock));

	slab->priorSlab = 0;
	slab->nextSlab = 0;
	slab->topBlock = (MemBlock*)(((unsigned char*)slab) + maxBytes + sizeof(MemSlab));
	slab->slabSize = maxBytes;

	slab->topBlock->rootSlab = slab;
	slab->topBlock->prevBlock = &slab->baseBlock;
	slab->topBlock->nextBlock = 0;
	slab->topBlock->blockSize = 0;

	slab->baseBlock.rootSlab = slab;
	slab->baseBlock.prevBlock = 0;
	slab->baseBlock.nextBlock = slab->topBlock;
	slab->baseBlock.blockSize = 0;

	gTotalSlabsAllocated += maxBytes;
	//LOG_INFO << "total slab bytes: " << gTotalSlabsAllocated;
	return slab;
	}

BSA_DLLEXPORT
void FORA_clib_freeSlab(MemSlab* slab)
	{
	do {
		gTotalSlabsAllocated -= slab->slabSize;

		MemSlab* next = slab->nextSlab;

		Ufora::Memory::bsa_free(slab);

		slab = next;
		} while (slab);

	//LOG_INFO << "total slab bytes: " << gTotalSlabsAllocated;
	}

BSA_DLLEXPORT
void* FORA_clib_allocMem(MemBlock** curBlock, uword_t ct)
	{
	MemBlock* b = *curBlock;

	//first see if we're the top block
	unsigned char* topAvail = (unsigned char*)b->nextBlock;
	unsigned char* req = b->data + b->blockSize + ct + sizeof(MemBlock);

	if (req <= topAvail)
		{
		MemBlock* oldNext = b->nextBlock;
		MemBlock* newBlock = (MemBlock*)(b->data + b->blockSize);

		oldNext->prevBlock = newBlock;
		b->nextBlock = newBlock;

		newBlock->prevBlock = b;
		newBlock->nextBlock = oldNext;
		newBlock->rootSlab = b->rootSlab;

		newBlock->blockSize = ct;

		*curBlock = newBlock;

		return newBlock->data;
		}

	//try going to the end of the slab
	if (b != b->rootSlab->topBlock->prevBlock)
		{
		*curBlock = b->rootSlab->topBlock->prevBlock;
		return FORA_clib_allocMem(curBlock, ct);
		}

	//we have to allocate elsewhere. go one slab "right" and try there. if not possible, new slab!
	if (!b->rootSlab->nextSlab)
		{
		b->rootSlab->nextSlab = FORA_clib_allocNewEmptySlab(std::max(b->rootSlab->slabSize, ct * 2));
		b->rootSlab->nextSlab->priorSlab = b->rootSlab;
		}

	*curBlock = b->rootSlab->nextSlab->topBlock->prevBlock;
	return FORA_clib_allocMem(curBlock, ct);
	}

BSA_DLLEXPORT
void FORA_clib_freeMem(MemBlock** curBlock, void* data)
	{
	MemBlock* toFree = (MemBlock*)(((unsigned char*)data) - sizeof(MemBlock));

	toFree->prevBlock->nextBlock = toFree->nextBlock;
	toFree->nextBlock->prevBlock = toFree->prevBlock;
	if (toFree == *curBlock)
		*curBlock = toFree->prevBlock;

	//back up along empty slabs
	while (*curBlock == &(*curBlock)->rootSlab->baseBlock && (*curBlock)->rootSlab->priorSlab)
		*curBlock = (*curBlock)->rootSlab->priorSlab->topBlock->prevBlock;

	}

}


