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

#include "../../core/Common.hppml"
#include "../../core/SymbolExport.hpp"

class MemBlock;
class MemSlab;

class MemBlock {
public:
		MemSlab* 			rootSlab;
		MemBlock*			prevBlock;
		MemBlock*			nextBlock;
		uword_t				blockSize;
		unsigned char		data[0]; //actual data for the block
};

class MemSlab {
public:
		MemSlab* 		priorSlab;
		MemSlab* 		nextSlab;
		uword_t			slabSize;
		MemBlock*	 	topBlock;
		MemBlock		baseBlock;

		//statistics and a check of validity of the pointer chain
		uword_t	used(void);
		void	validate(void);
};

extern "C" {

BSA_DLLEXPORT
MemSlab* FORA_clib_allocNewEmptySlab(uword_t maxBytes);

BSA_DLLEXPORT
void FORA_clib_freeSlab(MemSlab* slab);

BSA_DLLEXPORT
void* FORA_clib_allocMem(MemBlock** curBlock, uword_t ct);

BSA_DLLEXPORT
void FORA_clib_freeMem(MemBlock** curBlock, void* data);

};


