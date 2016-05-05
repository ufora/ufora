#pragma once

#include "../../core/IntegerTypes.hpp"

class MemoryPool;
class StackFrame;
class StackFrameSlab;

class StackFrameAllocator {
public:
	StackFrameAllocator(const StackFrameAllocator&) = delete;
	StackFrameAllocator& operator=(const StackFrameAllocator& in) = delete;

	StackFrameAllocator(size_t inSlabSize, MemoryPool* inPool);

	~StackFrameAllocator();

	//get a base pointer appropriate for passing into native FORA
	StackFrame** getMemBlockPtr();

	//free some memory
	void free(void* block);
	
	//allocate some memory
	void* allocate(size_t inByteCount);

	//release the memblock if not already released
	void releaseAll(void);

	void releaseTail(void);

	size_t totalBytesReserved(void);

	void freeSlabAndAllChildren(StackFrameSlab* slab);

	StackFrameSlab* allocateSlab(uword_t maxBytes);

private:
	void ensureInitialized(void);

	MemoryPool* mMemoryPool;

	//the current memory block that's on the top of the stack. This is the address that
	//getMemBlockPtr() points to
	StackFrame* mBaseMemBlock;
	
	//the root block in the sequence of slabs, so that we can know where to start deallocating
	//if we have to rip this down.
	StackFrame* mFirstMemBlock;

	size_t mSlabSize;
};
