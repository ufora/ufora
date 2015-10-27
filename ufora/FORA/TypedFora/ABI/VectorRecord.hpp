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

#include <stdint.h>
#include "../../../core/RefcountingPtr.hppml"
#include "../../../core/math/Nullable.hpp"
#include "../../../core/math/Hash.hpp"
#include "../../../core/math/IntegerSequence.hppml"
#include "../../Axioms/ReturnValue.hpp"

#include <boost/unordered_map.hpp>

class MemoryPool;
class VectorDataManager;
class JudgmentOnValue;
class JudgmentOnResult;
class ImplValContainer;

namespace Fora {

class PageletTree;

typedef RefcountingPtr<PageletTree> PageletTreePtr;

class BigVectorId;

}

namespace Fora {
namespace Interpreter {

class ExecutionContext;

}
}

namespace TypedFora {
namespace Abi {

class ForaValueArray;
class ForaValueArraySlice;
class BigVectorHandle;
class BigVectorPageLayout;
class VectorLoadRequest;
class VectorHandle;

typedef RefcountingPtr<VectorHandle> VectorHandlePtr;

class VectorRecordStorage {
public:
	VectorHandle*	mDataPtr;
	uint64_t		mSize;
	uint64_t		mOffset;
	int64_t			mStride;

};

class VectorRecord : protected VectorRecordStorage {
public:
	VectorRecord(VectorHandle* inPtr, uint64_t count, uint64_t offset, int64_t stride);
	
	VectorRecord(VectorHandle* inPtr);

	VectorRecord(VectorHandlePtr inPtr, uint64_t count, uint64_t offset, int64_t stride);
	
	VectorRecord(VectorHandlePtr inPtr);
	
	VectorRecord(const VectorRecord& in);

	~VectorRecord();

	static VectorRecord createWithinExecutionContext(ForaValueArray* array);

	static VectorRecord createVectorForEntirePageLayout(
										BigVectorPageLayout layout,
										Fora::Interpreter::ExecutionContext* withinThisContext
										);

	VectorRecord& operator=(const VectorRecord& inOther);

	VectorRecord()
		{
		mDataPtr = 0;
		mSize = 0;
		mOffset = 0;
		mStride = 1;
		}

	VectorHandle* dataPtr() const
		{
		return mDataPtr;
		}

	bool entirelyCoveredByJOV(const JudgmentOnValue& inJOV) const;

	Fora::ReturnValue<VectorRecord, VectorLoadRequest> 
			deepcopiedAndContiguous(MemoryPool* inPool, VectorDataManager* inVDM) const;

	Fora::ReturnValue<VectorRecord, VectorLoadRequest> 
			appropriateForConcatenation(MemoryPool* inPool, VectorDataManager* inVDM) const;

	static VectorRecord concatenate(
							const VectorRecord& inLHS, 
							const VectorRecord& inRHS, 
							MemoryPool* inPool,
							VectorDataManager* inVDM,
							hash_type inVectorHash
							);

	VectorRecord slice(
					Nullable<int64_t> low, 
					Nullable<int64_t> high, 
					Nullable<int64_t> stride
					) const;

	bool isCanonicallySliced() const;
	
	int64_t indexWithinHandle(int64_t ix) const
		{
		return offset() + stride() * ix;
		}

	IntegerSequence indicesWithinHandle() const
		{
		return IntegerSequence(size(), offset(), stride());
		}

	//return a vector with offset 0 and stride 1
	VectorRecord canonicallySliced(
					MemoryPool* inPool,
					VectorDataManager* inVDM,
					hash_type newVectorHash
					) const;

	//return the ValueArray and offset containing a given value. Returns 'null' in the first
	//pair field if it's empty
	TypedFora::Abi::ForaValueArraySlice sliceForOffset(int64_t index) const;

	VectorRecord append(MemoryPool* inPool, 
						ImplValContainer toAppend,
						VectorDataManager* inVDM,
						const boost::function0<hash_type>& hashCreatorFun
						);

	//if jovToAppend is untyped, dataToAppend should point to an ImplValContainer.
	//if jovToAppend is a constant or typed, dataToAppend should point to a value of the appropriate
	//type
	VectorRecord append(MemoryPool* inPool, 
						void* dataToAppend,
						JudgmentOnValue jovToAppend,
						VectorDataManager* inVDM,
						const boost::function0<hash_type>& hashCreatorFun
						);

	bool visitAnyLoadedValues(
		VectorDataManager* inVDM,
		boost::function2<void, ForaValueArray*, IntegerSequence> visitor,
		IntegerSequence subsequence
		);

	VectorRecord pagedPortion() const;

	VectorRecord pagedAndPageletTreePortion() const;

	VectorRecord pageletTreePortion() const;

	VectorRecord unpagedAndPageletTreePortion() const;

	VectorRecord unpagedPortion() const;

	bool allValuesAreLoaded() const;

	uint64_t size() const
		{
		return mSize;
		}

	int64_t stride() const
		{
		return mStride;
		}

	uint64_t offset() const
		{
		return mOffset;
		}

	//is this nonempty?
	operator bool() const
		{
		return mSize > 0;
		}

	bool operator < (const VectorRecord& in) const
		{
		if (mDataPtr < in.mDataPtr)
			return true;
		
		if (in.mDataPtr < mDataPtr)
			return false;
		
		if (mSize < in.mSize)
			return true;
		
		if (in.mSize < mSize)
			return false;
		
		if (mOffset < in.mOffset)
			return true;
		
		if (in.mOffset < mOffset)
			return false;
		
		if (mStride < in.mStride)
			return true;
		
		if (in.mStride < mStride)
			return false;
		
		return false;
		}

	bool operator== (const VectorRecord& in) const
		{
		return mDataPtr == in.mDataPtr && mSize == in.mSize && 
			mOffset == in.mOffset && mStride == in.mStride;
		}

	std::size_t unorderedMapHash() const
		{
		std::size_t seed = 0;

		boost::hash_combine(seed, mDataPtr);
		boost::hash_combine(seed, mSize);
		boost::hash_combine(seed, mStride);
		boost::hash_combine(seed, mOffset);

		return seed;
		}

	JudgmentOnResult jor() const;

	bool isEmptyOrVectorOfUint8() const;

	hash_type hash() const;

	hash_type vectorHandleHash() const;

	VectorRecord withVectorHash(hash_type hash) const;

	VectorRecord paged(MemoryPool* inPool, VectorDataManager* inVDM) const;

	ForaValueArray* unpagedValues() const;

	Fora::PageletTreePtr pageletTree() const;

	Fora::BigVectorId pagedValuesIdentity() const;
	
	int64_t pagedValueCount() const;

	int64_t unpagedValueCount() const;

	int64_t pageletTreeValueCount() const;

	int64_t pagedAndPageletTreeValueCount() const;

	int64_t unpagedAndPageletTreeValueCount() const;

};

//a VectorRecord held in the RefcountPool. Copying it doesn't require increfs.
class PooledVectorRecord : protected VectorRecordStorage {
public:
	PooledVectorRecord()
		{
		mDataPtr = 0;
		mSize = 0;
		mOffset = 0;
		mStride = 0;
		}
		
	PooledVectorRecord(VectorHandle* inPtr, uint64_t count, uint64_t offset, int64_t stride)
		{
		mDataPtr = inPtr;
		mSize = count;
		mOffset = offset;
		mStride = stride;
		}

	PooledVectorRecord(const PooledVectorRecord& in)
		{
		mDataPtr = in.mDataPtr;
		mStride = in.mStride;
		mOffset = in.mOffset;
		mSize = in.mSize;
		}

	PooledVectorRecord& operator=(const PooledVectorRecord& in)
		{
		mDataPtr = in.mDataPtr;
		mStride = in.mStride;
		mOffset = in.mOffset;
		mSize = in.mSize;
		
		return *this;
		}

	PooledVectorRecord slice(
					Nullable<int64_t> low, 
					Nullable<int64_t> high, 
					Nullable<int64_t> stride
					) const;

	const VectorRecord& getVectorRecord() const
		{
		return *(const VectorRecord*)this;
		}
};

}
}


namespace boost {

template<> 
class hash<TypedFora::Abi::VectorRecord> : 
		public std::unary_function<TypedFora::Abi::VectorRecord, std::size_t> {
public:
		std::size_t operator()(const TypedFora::Abi::VectorRecord& in) const
			{
			return in.unorderedMapHash();
			}
};

};

