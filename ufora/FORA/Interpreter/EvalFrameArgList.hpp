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

#include "InstructionPtr.hpp"
#include "../Judgment/JudgmentOnValue.hppml"

class MemBlockAllocator;

namespace Fora {
namespace Interpreter {

class ExecutionContext;
class Instruction;
class RefcountPool;

/*
a container which owns its own block of memory,
produced by ExecutionContext.allocMemBlock, on which it calls
placement new to push_back elements.
*/

class EvalFrameArgList {
public:
	ImplVal& operator[](uword_t index);

	const ImplVal& operator[](uword_t index) const;
	
	uword_t size() const;
	
	void copyPooledImplValsIntoFrame(const vector<ImplVal>& args);

	void unpackUnownedTupleIntoPooledArguments(const ImplVal& tupleImplVal, RefcountPool* refcountPool);

	//copy these values in
	void copyApplyArgsIntoArgSlots(const Fora::ApplyArgFrame& args, RefcountPool* refcountPool);

	void clear();
	
	void slice(uword_t ix);
	
	string toString() const;

	bool isCoveredBy(const ImmutableTreeVector<JOV>& jovs) const;

	static EvalFrameArgList* allocate(uword_t capacity, MemBlockAllocator& allocator);

	static void free(EvalFrameArgList* list, MemBlockAllocator& allocator);

	void addImplvalsToRefcountPool(RefcountPool* inPool);

	void push(const ImplVal& evalFrameArg);

private:
	uword_t mSize;
	uword_t mCapacity;
	//DANGER! member field-order is important here! we manipulate memory hanging off the end here!
	//mImplVals must be the last declared field. in order to avoid such worries, we
	//could instead hold a pointer to an alloc'd block.
	ImplVal mImplVals[1]; 
};

}
}

