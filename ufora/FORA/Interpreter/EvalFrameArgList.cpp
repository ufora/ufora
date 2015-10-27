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
#include "EvalFrameArgList.hpp"
#include "../Core/ExecutionContext.hppml"
#include "Instruction.hppml"
#include "../Core/RefcountPool.hppml"
#include "../Core/TupleCategory.hppml"
#include "../Core/ImplValContainerUtilities.hppml"

namespace Fora {
namespace Interpreter {

ImplVal& EvalFrameArgList::operator[](uword_t index)
	{
	lassert(index < mSize);
	return mImplVals[index];
	}

const ImplVal& EvalFrameArgList::operator[](uword_t index) const
	{
	lassert(index < mSize);
	return mImplVals[index];
	}

uword_t EvalFrameArgList::size() const
	{
	return mSize;
	}

void EvalFrameArgList::push(const ImplVal& evalFrameArg)
	{
	lassert(mSize + 1 <= mCapacity);

	mImplVals[mSize] = evalFrameArg;

	mSize++;
	}


void EvalFrameArgList::unpackUnownedTupleIntoPooledArguments(
											const ImplVal& tupleImplVal, 
											RefcountPool* pool
											)
	{
	clear();

	lassert(TupleCategory::isTuple(tupleImplVal));
	
	typedef TupleCategory::iterator tuple_iterator;

	for (tuple_iterator it = tuple_iterator::begin(tupleImplVal), 
					it2 = tuple_iterator::end(tupleImplVal); it != it2; ++it)
		push(pool->add(*it));
	}

void EvalFrameArgList::copyApplyArgsIntoArgSlots(
											const Fora::ApplyArgFrame& args,
											RefcountPool* pool
											)
	{
	lassert(args.getApplyArgs().size() <= mCapacity);

	for (long k = 0; k < args.getApplyArgs().size(); k++)
		push(pool->add(args.getApplyArgs()[k].value()));
	}

string EvalFrameArgList::toString() const
	{
	ostringstream s;
	s << "EvalFrameArgList (size=" << mSize << ", capacity=" << mCapacity << ") containing: ";
	for (long k = 0; k < mSize; k++)
		{
		s << mImplVals[k].toString() << ", ";
		}
	s << "\n";
	return s.str();
	}

void EvalFrameArgList::copyPooledImplValsIntoFrame(const vector<ImplVal>& args)
	{
	clear();
	for (long k = 0; k < args.size(); k++)
		push(args[k]);
	}

void EvalFrameArgList::clear()
	{
	mSize = 0;
	}

void EvalFrameArgList::slice(uword_t ix)
	{
	if (ix >= mSize) 
		return;

	mSize = ix;
	}

bool EvalFrameArgList::isCoveredBy(const ImmutableTreeVector<JOV>& jovs) const
	{
	for (long k = 0; k < jovs.size(); k++)
		if (!jovs[k].covers(mImplVals[k]))
			return false;

	return true;
	}

EvalFrameArgList* EvalFrameArgList::allocate(uword_t capacity, MemBlockAllocator& allocator)
	{
	EvalFrameArgList* newEvalFrameArgListPtr =
		(EvalFrameArgList*) allocator.allocate(
								sizeof(EvalFrameArgList) + sizeof(ImplVal) * (capacity * 2 + 1)
								);
	newEvalFrameArgListPtr->mSize = 0;
	newEvalFrameArgListPtr->mCapacity = capacity;

	return newEvalFrameArgListPtr;
	}

void EvalFrameArgList::free(EvalFrameArgList* list, MemBlockAllocator& allocator)
	{
	allocator.free(list);
	}

void EvalFrameArgList::addImplvalsToRefcountPool(RefcountPool* inPool)
	{
	for (long k = 0; k < mSize;k++)
		inPool->add(mImplVals[k]);
	}

}
}

