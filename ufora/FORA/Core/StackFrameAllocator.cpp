#include "StackFrameAllocator.hpp"
#include "StackFrame.hpp"
#include "MemoryPool.hpp"
#include "../../core/Logging.hpp"
#include "../../core/lassert.hpp"

StackFrameAllocator::StackFrameAllocator(size_t inSlabSize, MemoryPool* inMemPool) : 
		mSlabSize(inSlabSize),
		mBaseMemBlock(0),
		mFirstMemBlock(0),
		mMemoryPool(inMemPool)
	{
	}

StackFrameAllocator::~StackFrameAllocator()
	{
	releaseAll();
	}

//get a base pointer appropriate for passing into native FORA
StackFrame** StackFrameAllocator::getMemBlockPtr()
	{
	ensureInitialized();

	return &mBaseMemBlock;
	}

//free some memory
void StackFrameAllocator::free(void* block)
	{
	lassert_dump(mFirstMemBlock, "StackFrameAllocator is empty");

	FORA_clib_freeStackFrame(&mBaseMemBlock, block);
	}

//allocate some memory
void* StackFrameAllocator::allocate(size_t inByteCount)
	{
	ensureInitialized();

	return FORA_clib_allocateStackFrame(&mBaseMemBlock, inByteCount);
	}

//release the memblock if not already released
void StackFrameAllocator::releaseAll(void)
	{
	if (mFirstMemBlock)
		{
		freeSlabAndAllChildren(mFirstMemBlock->rootSlab);
		mFirstMemBlock = 0;
		mBaseMemBlock = 0;
		}
	}

void StackFrameAllocator::ensureInitialized(void)
	{
	if (!mBaseMemBlock)
		{
		StackFrameSlab* slab = allocateSlab(mSlabSize);
		mBaseMemBlock = &slab->baseBlock;
		mFirstMemBlock = mBaseMemBlock;
		}
	}

size_t StackFrameAllocator::totalBytesReserved(void)
	{
	if (!mBaseMemBlock)
		return 0;
	
	size_t tr = 0;

	StackFrameSlab* slab = mFirstMemBlock->rootSlab;
	while (slab)
		{
		tr = tr + slab->slabSize;
		slab = slab->nextSlab;
		}

	return tr;
	}

StackFrameSlab* StackFrameAllocator::allocateSlab(uword_t maxBytes)
	{
	StackFrameSlab* slab = (StackFrameSlab*)mMemoryPool->allocate(maxBytes + sizeof(StackFrameSlab) + sizeof(StackFrame));

	slab->allocator = this;
	slab->priorSlab = 0;
	slab->nextSlab = 0;
	slab->topBlock = (StackFrame*)(((unsigned char*)slab) + maxBytes + sizeof(StackFrameSlab));
	slab->slabSize = maxBytes;

	slab->topBlock->rootSlab = slab;
	slab->topBlock->prevBlock = &slab->baseBlock;
	slab->topBlock->nextBlock = 0;
	slab->topBlock->blockSize = 0;
	
	slab->baseBlock.rootSlab = slab;
	slab->baseBlock.prevBlock = 0;
	slab->baseBlock.nextBlock = slab->topBlock;
	slab->baseBlock.blockSize = 0;

	return slab;
	}

void StackFrameAllocator::freeSlabAndAllChildren(StackFrameSlab* slab)
	{
	do {
		StackFrameSlab* next = slab->nextSlab;

		mMemoryPool->free((uint8_t*)slab);

		slab = next;
		} while (slab);
	}

void StackFrameAllocator::releaseTail(void)
	{
	if (!mBaseMemBlock)
		return;

	StackFrameSlab* lastSlab = mBaseMemBlock->rootSlab;
	lassert(lastSlab);

	while (lastSlab->nextSlab)
		lastSlab = lastSlab->nextSlab;

	while (lastSlab && lastSlab->isEmpty() && lastSlab != mBaseMemBlock->rootSlab)
		{
		StackFrameSlab* priorSlab = lastSlab->priorSlab;
		mMemoryPool->free((uint8_t*)lastSlab);
		priorSlab->nextSlab = nullptr;
		lastSlab = priorSlab;
		}

	if (mFirstMemBlock == mBaseMemBlock)
		releaseAll();
	}