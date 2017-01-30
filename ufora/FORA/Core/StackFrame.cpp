#include "StackFrame.hpp"
#include "StackFrameAllocator.hpp"
#include "../../core/lassert.hpp"
#include "../../core/Memory.hpp"

StackFrameAllocator* StackFrame::allocator()
	{
	return rootSlab->allocator;
	}

//statistics and a check of validity of the pointer chain
uword_t	StackFrameSlab::used(void)
	{
	uword_t tr = 0;

	StackFrame* b = &baseBlock;

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

void	StackFrameSlab::validate(void)
	{
	using namespace std;

	StackFrame* b = &baseBlock;

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

bool StackFrameSlab::isEmpty() const
	{
	return baseBlock.nextBlock == topBlock;
	}

extern "C" {

BSA_DLLEXPORT
void* FORA_clib_allocateStackFrame(StackFrame** curBlock, uword_t ct)
	{
	StackFrame* b = *curBlock;

	//first see if we're the top block
	unsigned char* topAvail = (unsigned char*)b->nextBlock;
	unsigned char* req = b->data + b->blockSize + ct + sizeof(StackFrame);

	if (req <= topAvail)
		{
		StackFrame* oldNext = b->nextBlock;
		StackFrame* newBlock = (StackFrame*)(b->data + b->blockSize);

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
		return FORA_clib_allocateStackFrame(curBlock, ct);
		}

	//we have to allocate elsewhere. go one slab "right" and try there. if not possible, new slab!
	if (!b->rootSlab->nextSlab)
		{
		b->rootSlab->nextSlab = b->rootSlab->allocator->allocateSlab(std::max(b->rootSlab->slabSize, ct * 2));
		b->rootSlab->nextSlab->priorSlab = b->rootSlab;
		}

	*curBlock = b->rootSlab->nextSlab->topBlock->prevBlock;
	return FORA_clib_allocateStackFrame(curBlock, ct);
	}

BSA_DLLEXPORT
void FORA_clib_freeStackFrame(StackFrame** curBlock, void* data)
	{
	StackFrame* toFree = (StackFrame*)(((unsigned char*)data) - sizeof(StackFrame));

	toFree->prevBlock->nextBlock = toFree->nextBlock;
	toFree->nextBlock->prevBlock = toFree->prevBlock;
	if (toFree == *curBlock)
		*curBlock = toFree->prevBlock;

	//back up along empty slabs
	while (*curBlock == &(*curBlock)->rootSlab->baseBlock && (*curBlock)->rootSlab->priorSlab)
		*curBlock = (*curBlock)->rootSlab->priorSlab->topBlock->prevBlock;
	}

}

