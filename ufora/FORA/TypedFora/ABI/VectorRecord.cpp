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
#include "VectorRecord.hpp"
#include "VectorHandle.hpp"
#include "BigVectorHandle.hppml"
#include "ForaValueArray.hppml"
#include "VectorLoadRequest.hppml"
#include "BigVectorLayouts.hppml"
#include "../../Core/RefcountPool.hppml"
#include "../../VectorDataManager/VectorDataManager.hppml"
#include "../../VectorDataManager/PageletTree.hppml"
#include "../../Core/ExecutionContext.hppml"
#include "../../Core/MemoryPool.hpp"
#include "../../../core/math/RandomHashGenerator.hpp"


namespace TypedFora {
namespace Abi {

VectorRecord::VectorRecord(VectorHandle* inPtr)
	{
	mDataPtr = inPtr;
	mSize = inPtr ? inPtr->size() : 0;
	mOffset = 0;
	mStride = 1;

	if (mDataPtr)
		mDataPtr->incrementRefcount();
	}

VectorRecord::VectorRecord(VectorHandle* inPtr, uint64_t count, uint64_t offset, int64_t stride)
	{
	mDataPtr = inPtr;
	mSize = count;
	mOffset = offset;
	mStride = stride;

	if (mDataPtr)
		mDataPtr->incrementRefcount();
	}

VectorRecord::VectorRecord(VectorHandlePtr inPtr)
	{
	mDataPtr = inPtr.ptr();
	mSize = !inPtr.isEmpty() ? inPtr->size() : 0;
	mOffset = 0;
	mStride = 1;

	if (mDataPtr)
		mDataPtr->incrementRefcount();
	}

VectorRecord::VectorRecord(VectorHandlePtr inPtr, uint64_t count, uint64_t offset, int64_t stride)
	{
	mDataPtr = inPtr.ptr();
	mSize = count;
	mOffset = offset;
	mStride = stride;

	if (mDataPtr)
		mDataPtr->incrementRefcount();
	}

VectorRecord::VectorRecord(const VectorRecord& in)
	{
	mDataPtr = in.mDataPtr;
	mStride = in.mStride;
	mOffset = in.mOffset;
	mSize = in.mSize;

	if (mDataPtr)
		mDataPtr->incrementRefcount();
	}

VectorRecord::~VectorRecord()
	{
	if (mDataPtr)
		mDataPtr->decrementRefcount();
	}

Fora::BigVectorId VectorRecord::pagedValuesIdentity() const
	{
	if (mDataPtr)
		return mDataPtr->pagedValuesIdentity();
	else
		return Fora::BigVectorId();
	}

JudgmentOnResult VectorRecord::jor() const
	{
	if (!mDataPtr)
		return JudgmentOnResult();

	return mDataPtr->jor();
	}

bool VectorRecord::isEmptyOrVectorOfUint8() const
	{
	if (!mDataPtr)
		return true;

	return mDataPtr->isEmptyOrVectorOfUint8();
	}

VectorRecord& VectorRecord::operator=(const VectorRecord& inOther)
	{
	if (inOther.mDataPtr != mDataPtr)
		{
		if (inOther.mDataPtr)
			inOther.mDataPtr->incrementRefcount();

		if (mDataPtr)
			mDataPtr->decrementRefcount();

		mDataPtr = inOther.mDataPtr;
		}

	mSize = inOther.mSize;
	mStride = inOther.mStride;
	mOffset = inOther.mOffset;

	return *this;
	}

int64_t VectorRecord::pagedValueCount() const
	{
	if (!mDataPtr)
		return 0;
	return mDataPtr->pagedValueCount();
	}

int64_t VectorRecord::unpagedValueCount() const
	{
	if (!mDataPtr)
		return 0;
	return mDataPtr->unpagedValueCount();
	}

int64_t VectorRecord::pageletTreeValueCount() const
	{
	if (!mDataPtr)
		return 0;
	return mDataPtr->pageletTreeValueCount();
	}

int64_t VectorRecord::pagedAndPageletTreeValueCount() const
	{
	if (!mDataPtr)
		return 0;
	return mDataPtr->pagedAndPageletTreeValueCount();
	}

int64_t VectorRecord::unpagedAndPageletTreeValueCount() const
	{
	if (!mDataPtr)
		return 0;
	return mDataPtr->unpagedAndPageletTreeValueCount();
	}

ForaValueArray* VectorRecord::unpagedValues() const
	{
	if (!mDataPtr)
		return nullptr;

	return mDataPtr->unpagedValues();
	}

Fora::PageletTreePtr VectorRecord::pageletTree() const
	{
	if (!mDataPtr)
		return Fora::PageletTreePtr();

	return mDataPtr->pageletTree();
	}

hash_type VectorRecord::hash() const
	{
	if (!mDataPtr)
		return hash_type();

	return mDataPtr->hash() + hash_type(mSize, mOffset, mStride);
	}

hash_type VectorRecord::vectorHandleHash() const
	{
	if (!mDataPtr)
		return hash_type();

	return mDataPtr->hash();
	}

TypedFora::Abi::ForaValueArraySlice VectorRecord::sliceForOffset(int64_t index) const
	{
	lassert(mDataPtr);

	return mDataPtr->sliceForOffset(index * mStride + mOffset).compose(
		RangeToIntegerSequence(0, size(), offset(), stride())
		);
	}

VectorRecord VectorRecord::append(
						MemoryPool* inPool,
						ImplValContainer toAppend,
						VectorDataManager* inVDM,
						const boost::function0<hash_type>& hashCreatorFun
						)
	{
	if (!mDataPtr)
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(toAppend);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				Fora::BigVectorId(),
				Fora::PageletTreePtr(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}

	if (stride() == 1 && size() + offset() == mDataPtr->size() && mDataPtr->unpagedValues()
			&& mDataPtr->unpagedValues()->isWriteable())
		{
		//we can append directly
		mDataPtr->unpagedValues()->append(toAppend);
		mDataPtr->valueAppendedToUnpagedData();
		return VectorRecord(mDataPtr, mSize+1, mOffset, 1);
		}

	if (!isCanonicallySliced())
		return canonicallySliced(inPool, inVDM, hashCreatorFun())
			.append(inPool, toAppend, inVDM, hashCreatorFun);

	if (mDataPtr->unpagedValues())
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(*mDataPtr->unpagedValues());
		array->append(toAppend);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				mDataPtr->pagedValuesIdentity(),
				mDataPtr->pageletTree(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}
	else
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(toAppend);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				mDataPtr->pagedValuesIdentity(),
				mDataPtr->pageletTree(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}
	}

VectorRecord VectorRecord::append(
						MemoryPool* inPool,
						void* dataToAppend,
						JOV jovToAppend,
						VectorDataManager* inVDM,
						const boost::function0<hash_type>& hashCreatorFun
						)
	{
	if (!mDataPtr)
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(jovToAppend, (uint8_t*)dataToAppend, 1, 0);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				Fora::BigVectorId(),
				Fora::PageletTreePtr(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}

	if (stride() == 1 && size() + offset() == mDataPtr->size() && mDataPtr->isWriteable())
		{
		mDataPtr->makeSpaceForNewUnpagedValues(inVDM);

		lassert(mDataPtr->unpagedValues());

		mDataPtr->unpagedValues()->append(jovToAppend, (uint8_t*)dataToAppend, 1, 0);
		mDataPtr->valueAppendedToUnpagedData();

		return VectorRecord(mDataPtr, mSize+1, mOffset, 1);
		}

	if (!isCanonicallySliced())
		return canonicallySliced(inPool, inVDM, hashCreatorFun())
			.append(inPool, dataToAppend, jovToAppend, inVDM, hashCreatorFun);

	if (mDataPtr->unpagedValues())
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(*mDataPtr->unpagedValues());
		array->append(jovToAppend, (uint8_t*)dataToAppend, 1, 0);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				mDataPtr->pagedValuesIdentity(),
				mDataPtr->pageletTree(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}
	else
		{
		ForaValueArray* array = ForaValueArray::Empty(inPool);
		array->append(jovToAppend, (uint8_t*)dataToAppend, 1, 0);

		return VectorRecord(
			inPool->construct<VectorHandle>(
				mDataPtr->pagedValuesIdentity(),
				mDataPtr->pageletTree(),
				array,
				inPool,
				hashCreatorFun()
				)
			);
		}
	}

Fora::ReturnValue<VectorRecord, VectorLoadRequest>
		VectorRecord::appropriateForConcatenation(MemoryPool* inPool, VectorDataManager* inVDM) const
	{
	//if we are a very small slice of a vector page, or if we are a very small vector page,
	//then call 'deepcopied and contiguous'
	if (!mDataPtr || mDataPtr->pagedValueCount() == 0)
		return Fora::slot0(*this);

	if (mDataPtr->needsDeepcopyBeforeConcatenation(inVDM, indicesWithinHandle()))
		return deepcopiedAndContiguous(inPool, inVDM);

	return Fora::slot0(*this);
	}

VectorRecord VectorRecord::concatenate(
							const VectorRecord& inLHS,
							const VectorRecord& inRHS,
							MemoryPool* inPool,
							VectorDataManager* inVDM,
							hash_type inVectorHash
							)
	{
	if (!inLHS)
		return inRHS;
	if (!inRHS)
		return inLHS;

	if (!inLHS.isCanonicallySliced())
		return concatenate(
			inLHS.canonicallySliced(inPool, inVDM, inVectorHash + hash_type(0, 1, 0)),
			inRHS,
			inPool,
			inVDM,
			inVectorHash
			);

	if (!inRHS.isCanonicallySliced())
		return concatenate(
			inLHS,
			inRHS.canonicallySliced(inPool, inVDM, inVectorHash + hash_type(0, 2, 0)),
			inPool,
			inVDM,
			inVectorHash
			);

	return VectorRecord(
		VectorHandle::concatenate(
			inLHS.mDataPtr,
			inLHS.mSize,
			inRHS.mDataPtr,
			inRHS.mSize,
			inPool,
			inVDM,
			inVectorHash
			)
		);
	}

VectorRecord VectorRecord::slice(
					Nullable<int64_t> nLow,
					Nullable<int64_t> nHigh,
					Nullable<int64_t> nStride
					)  const
	{
	if (!mDataPtr)
		return VectorRecord();

	if (nStride && *nStride == 0)
		return VectorRecord();

	IntegerSequence sequenceToUse =
		IntegerSequence(size(), offset(), stride()).slice(nLow, nHigh, nStride);

	if (!sequenceToUse.size())
		return VectorRecord();

	return VectorRecord(
		mDataPtr,
		sequenceToUse.size(),
		sequenceToUse.offset(),
		sequenceToUse.stride()
		);
	}

PooledVectorRecord PooledVectorRecord::slice(
					Nullable<int64_t> nLow,
					Nullable<int64_t> nHigh,
					Nullable<int64_t> nStride
					)  const
	{
	if (!mDataPtr)
		return PooledVectorRecord();

	if (nStride && *nStride == 0)
		return PooledVectorRecord();

	IntegerSequence sequenceToUse =
		IntegerSequence(mSize, mOffset, mStride).slice(nLow, nHigh, nStride);

	if (!sequenceToUse.size())
		return PooledVectorRecord();

	return PooledVectorRecord(
		mDataPtr,
		sequenceToUse.size(),
		sequenceToUse.offset(),
		sequenceToUse.stride()
		);
	}

bool VectorRecord::isCanonicallySliced() const
	{
	return offset() == 0 && stride() == 1 && (!size() && !dataPtr() || size() == dataPtr()->size());
	}

VectorRecord VectorRecord::canonicallySliced(
					MemoryPool* inPool,
					VectorDataManager* inVDM,
					hash_type newVectorHash
					)  const
	{
	if (!mDataPtr)
		return VectorRecord();

	VectorRecord res(
		mDataPtr->slice(
			indicesWithinHandle(),
			inPool,
			inVDM,
			newVectorHash
			)
		);

	lassert_dump(
		res.size() == size(),
		"Slicing a vector of size " << mDataPtr->size() << " with " << prettyPrintString(indicesWithinHandle())
			<< " produced " << res.size() << ". Expected " << indicesWithinHandle().size()
			<< "\n\nHandle = "
			<< mDataPtr
		);

	return res;
	}

VectorRecord VectorRecord::createWithinExecutionContext(ForaValueArray* array)
	{
	Fora::Interpreter::ExecutionContext* curExecutionContext =
			Fora::Interpreter::ExecutionContext::currentExecutionContext();

	MemoryPool* pool = curExecutionContext->getMemoryPool();

	return VectorRecord(
		pool->construct<VectorHandle>(
			Fora::BigVectorId(),
			Fora::PageletTreePtr(),
			array,
			pool,
			curExecutionContext->newVectorHash()
			)
		);
	}

VectorRecord VectorRecord::createVectorForEntirePageLayout(
									BigVectorPageLayout layout,
									Fora::Interpreter::ExecutionContext* withinThisContext
									)
	{
	MemoryPool* pool = (
		withinThisContext ?
			withinThisContext->getMemoryPool()
		:	MemoryPool::getFreeStorePool()
		);

	if (withinThisContext)
		withinThisContext->getVDM().getBigVectorLayouts()->registerNewLayout(layout);

	return VectorRecord(
		pool->construct<VectorHandle>(
			layout.identity(),
			Fora::PageletTreePtr(),
			(ForaValueArray*)0,
			pool,
			RandomHashGenerator::singleton().generateRandomHash()
			)
		);
	}

VectorRecord VectorRecord::pagedPortion() const
	{
	IntegerSequence curSlice(size(), offset(), stride());
	IntegerSequence restrictedSlice = curSlice.intersect(IntegerSequence(pagedValueCount()));

	if (!restrictedSlice.size())
		return VectorRecord();

	return VectorRecord(
		dataPtr(),
		restrictedSlice.size(),
		restrictedSlice.offset(),
		restrictedSlice.stride()
		);
	}

VectorRecord VectorRecord::pagedAndPageletTreePortion() const
	{
	IntegerSequence curSlice(size(), offset(), stride());
	IntegerSequence restrictedSlice = curSlice.intersect(IntegerSequence(pagedAndPageletTreeValueCount()));

	if (!restrictedSlice.size())
		return VectorRecord();

	return VectorRecord(
		dataPtr(),
		restrictedSlice.size(),
		restrictedSlice.offset(),
		restrictedSlice.stride()
		);
	}

VectorRecord VectorRecord::unpagedPortion() const
	{
	IntegerSequence curSlice(size(), offset(), stride());
	IntegerSequence restrictedSlice = curSlice.intersect(
		IntegerSequence(
			unpagedValueCount(),
			pagedAndPageletTreeValueCount()
			)
		);

	if (!restrictedSlice.size())
		return VectorRecord();

	return VectorRecord(
		dataPtr(),
		restrictedSlice.size(),
		restrictedSlice.offset(),
		restrictedSlice.stride()
		);
	}

VectorRecord VectorRecord::pageletTreePortion() const
	{
	IntegerSequence curSlice(size(), offset(), stride());
	IntegerSequence restrictedSlice = curSlice.intersect(
		IntegerSequence(
			pageletTreeValueCount(),
			pagedValueCount()
			)
		);

	if (!restrictedSlice.size())
		return VectorRecord();

	return VectorRecord(
		dataPtr(),
		restrictedSlice.size(),
		restrictedSlice.offset(),
		restrictedSlice.stride()
		);
	}

VectorRecord VectorRecord::unpagedAndPageletTreePortion() const
	{
	IntegerSequence curSlice(size(), offset(), stride());
	IntegerSequence restrictedSlice = curSlice.intersect(
		IntegerSequence(
			unpagedAndPageletTreeValueCount(),
			pagedValueCount()
			)
		);

	if (!restrictedSlice.size())
		return VectorRecord();

	return VectorRecord(
		dataPtr(),
		restrictedSlice.size(),
		restrictedSlice.offset(),
		restrictedSlice.stride()
		);
	}

bool VectorRecord::allValuesAreLoaded() const
	{
	if (!dataPtr() || !dataPtr()->pagedAndPageletTreeValueCount())
		return true;

	IntegerSequence curSlice(size(), offset(), stride());

	IntegerSequence restrictedSlice = curSlice.intersect(IntegerSequence(pagedAndPageletTreeValueCount()));

	if (restrictedSlice.size() == 0)
		return true;

	Nullable<long> slotIndex;
	Fora::Interpreter::ExecutionContext* context = Fora::Interpreter::ExecutionContext::currentExecutionContext();

	if (context)
		slotIndex = context->getCurrentBigvecSlotIndex();
	else
		slotIndex = 0;

	lassert(slotIndex);

	if (!dataPtr()->bigvecHandleForSlot(*slotIndex))
		return false;

	bool tr = dataPtr()->
		bigvecHandleForSlot(*slotIndex)->allValuesAreLoadedBetween(
			restrictedSlice.smallestValue(),
			restrictedSlice.largestValue() + 1
			);

	return tr;
	}

namespace {

Nullable<pair<int64_t, int64_t> > extractPageableIndices(
								const BigVectorPageLayout& layout,
								uint64_t maxPageSizeInBytes
								)
	{
	for (long k = 0; k + 1 < layout.vectorIdentities().size(); k++)
		{
		Fora::PageId firstPage = layout.vectorIdentities()[k].vector().getPage();
		Fora::PageId secondPage = layout.vectorIdentities()[k+1].vector().getPage();

		if (firstPage.bytecount() + secondPage.bytecount() < maxPageSizeInBytes)
			{
			long low = k;
			long high = k+2;
			long bytecount = firstPage.bytecount() + secondPage.bytecount();

			while (high < layout.vectorIdentities().size() &&
					bytecount + layout.vectorIdentities()[high].vector().getPage().bytecount() <
																				maxPageSizeInBytes)
				{
				bytecount += layout.vectorIdentities()[high].vector().getPage().bytecount();
				high++;
				}

			return null() << pair<int64_t, int64_t>(layout.startIndex(low), layout.startIndex(high));
			}
		}

	return null();
	}

}

Fora::ReturnValue<VectorRecord, VectorLoadRequest>
			VectorRecord::deepcopiedAndContiguous(MemoryPool* inPool, VectorDataManager* inVDM) const
	{
	if (!dataPtr())
		return Fora::slot0(*this);

	lassert(!inPool->isBigVectorHandle());

	VectorHandle* handle = dataPtr();

	if (!allValuesAreLoaded())
		return Fora::slot1(VectorLoadRequest(*this));

	ForaValueArray* array = ForaValueArray::Empty(inPool);

	int64_t curIndex = 0;

	while (curIndex < size())
		{
		TypedFora::Abi::ForaValueArraySlice slice = sliceForOffset(curIndex);

		lassert(slice.mapping().indexIsValid(curIndex));

		lassert_dump(
			slice.array(),
			"We should have guaranteed that this value was loaded by calling 'allValuesAreLoaded'"
			);

		Nullable<int64_t> unmappedIndex =
			slice.firstValueNotLoadedInRange(
				curIndex,
				slice.mapping().highIndex()
				);

		lassert_dump(
			!unmappedIndex,
			"Index " << *unmappedIndex << " is unmapped in "
				<< prettyPrintString(slice) << " of size " << size()
			);

		if (slice.mapping().stride() == 1)
			{
			array->append(
				*slice.array(),
				slice.mapping().offsetForIndex(curIndex),
				slice.mapping().offsetForIndex(slice.mapping().highIndex())
				);
			}
		else
			{
			while (curIndex < slice.mapping().highIndex())
				{
				int64_t indexInTarget = slice.mapping().offsetForIndex(curIndex);
				array->append(*slice.array(), indexInTarget, indexInTarget+1);
				curIndex++;
				}
			}

		curIndex = slice.mapping().highIndex();
		}

	lassert(array->size() == size());

	return Fora::slot0(
		VectorRecord(
			inPool->construct<VectorHandle>(
				Fora::BigVectorId(),
				Fora::PageletTreePtr(),
				array,
				inPool,
				vectorHandleHash()
				)
			)
		);
	}

VectorRecord VectorRecord::paged(MemoryPool* inPool, VectorDataManager* inVDM) const
	{
	if (!mDataPtr)
		return VectorRecord();

	return VectorRecord(mDataPtr->paged(inPool, inVDM), mSize, mOffset, mStride);
	}

bool VectorRecord::entirelyCoveredByJOV(const JudgmentOnValue& inJOV) const
	{
	if (!dataPtr())
		return true;

	VectorHandle* handle = dataPtr();

	lassert(allValuesAreLoaded());

	int64_t curIndex = 0;

	while (curIndex < size())
		{
		TypedFora::Abi::ForaValueArraySlice slice = sliceForOffset(curIndex);

		lassert_dump(
			slice.array(),
			"We should have guaranteed that this value was loaded by calling 'allValuesAreLoaded'"
			);

		if (slice.mapping().stride() == 1)
			{
			bool allAreCovered = true;

			auto visitor = [&](const PackedForaValues& vals) {
				if (!allAreCovered || !inJOV.covers(vals.elementJOV()))
					allAreCovered = false;
				};

			slice.array()->visitValuesSequentially(
				visitor,
				slice.mapping().range().offset(),
				slice.mapping().range().endValue()
				);

			if (!allAreCovered)
				return false;
			}
		else
			{
			while (curIndex < slice.mapping().highIndex())
				{
				if (!inJOV.covers(slice.jovFor(curIndex)))
					return false;
				curIndex++;
				}
			}

		curIndex = slice.mapping().highIndex();
		}

	return true;
	}

bool VectorRecord::visitAnyLoadedValues(
		VectorDataManager* inVDM,
		boost::function2<void, ForaValueArray*, IntegerSequence> visitor,
		IntegerSequence subsequence
		)
	{
	if (!dataPtr())
		return false;

	subsequence = subsequence.intersect(IntegerSequence(size()));

	IntegerSequence subsequenceWithinVH(
		subsequence.size(),
		offset() + subsequence.offset() * stride(),
		stride() * subsequence.stride()
		);

	return dataPtr()->visitAnyLoadedValues(
		inVDM,
		visitor,
		subsequenceWithinVH
		);
	}


}
}

