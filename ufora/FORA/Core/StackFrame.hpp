#pragma once

#include "../../core/Common.hppml"
#include "../../core/SymbolExport.hpp"

class StackFrame;
class StackFrameSlab;
class StackFrameAllocator;

class StackFrame {
public:
	StackFrameSlab* rootSlab;
	StackFrame* prevBlock;
	StackFrame* nextBlock;
	uword_t blockSize;
	unsigned char data[0]; //actual data for the block

	StackFrameAllocator* allocator();
};

class StackFrameSlab {
public:
	StackFrameSlab* priorSlab;
	StackFrameSlab* nextSlab;
	uword_t slabSize;
	StackFrame* topBlock;
	StackFrameAllocator* allocator;
	
	StackFrame baseBlock;

	bool isEmpty() const;

	//statistics and a check of validity of the pointer chain
	uword_t	used(void);

	void validate(void);
};

extern "C" {

BSA_DLLEXPORT
void* FORA_clib_allocateStackFrame(StackFrame** curBlock, uword_t ct);

BSA_DLLEXPORT
void FORA_clib_freeStackFrame(StackFrame** curBlock, void* data);

};

