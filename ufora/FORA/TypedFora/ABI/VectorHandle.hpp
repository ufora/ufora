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

#include "../../../core/Common.hppml"
#include "../../../core/SymbolExport.hpp"
#include "../../Vector/VectorDataID.hppml"
#include "../../../core/serialization/Serialization.hpp"
#include "../../Core/Type.hppml"
#include "../../../core/AtomicOps.hpp"
#include "../../../core/SymbolExport.hpp"
#include "../../../core/PolymorphicSharedPtr.hpp"
#include "../../Axioms/ReturnValue.hpp"
#include "../../../core/RefcountingPtr.hppml"
#include "HomogenousVectorStash.hppml"
#include "BigVectorPageLayout.hppml"
#include <stdint.h>
#include <boost/bind.hpp>

class MemoryPool;

class JudgmentOnResult;

class VectorPage;

class NativeType;

class VectorDataManager;

namespace Fora {

class Pagelet;

class PageletTree;

typedef RefcountingPtr<PageletTree> PageletTreePtr;

}

namespace TypedFora {
namespace Abi {

class ForaValueArray;
class BigVectorHandle;

class ForaValueArraySlice;

class VectorHandle;

typedef RefcountingPtr<VectorHandle> VectorHandlePtr;

class VectorHandle {
public:
	const static long kMaxBigVectorHandles = 64;

	enum class LoadCheckResult {
		Failed,
		Success,
		UnmapAllAndTryAgain
	};

	//construct a new VectorHandle. Handles are initialized with refcount zero.
	VectorHandle(
		Fora::BigVectorId identity,
		Fora::PageletTreePtr pageletTree,
		ForaValueArray* unpagedValues,
		MemoryPool* owningMemoryPool,
		hash_type vectorHash
		);

	VectorHandle(
		Fora::BigVectorId identity,
		Fora::PageletTreePtr pageletTree,
		boost::shared_ptr<Fora::Pagelet> unpagedValues,
		MemoryPool* owningMemoryPool,
		hash_type vectorHash
		);

	~VectorHandle();

	JudgmentOnResult jor() const;

	hash_type hash() const { return mVectorHash; };

	uint64_t size() const;

	AO_t refcount() const
		{
		return mRefcount;
		}

	void assertHasNoReferencesToPages();

	bool needsDeepcopyBeforeConcatenation(
					VectorDataManager* inVDM,
					IntegerSequence sequenceInHandle
					);

	VectorHandlePtr slice(
					IntegerSequence seq,
					MemoryPool* inPool,
					VectorDataManager* inVDM,
					hash_type newVectorHash
					);

	void setSlotToStatusUnreported(long slotIndex);

	static VectorHandlePtr concatenate(
					VectorHandle* lhs,
					int64_t lhsValuesUsed,
					VectorHandle* rhs,
					int64_t rhsValuesUsed,
					MemoryPool* inPool,
					VectorDataManager* inVDM,
					hash_type newVectorHash
					);

	ForaValueArraySlice sliceForOffset(int64_t index) const;

	pair<ForaValueArray*, int64_t> arrayAndOffsetFor(int64_t index) const;

	class RefcountExpectation {
		int m;
	public:
		enum  { NonzeroRefcount, ZeroRefcount, NoExpectation };

		RefcountExpectation(int i) : m(i) {}
		operator int () const { return m; }
		bool operator==(const int i) { return m == i; }
	};

	void assertValid(RefcountExpectation expectation =
									RefcountExpectation::NonzeroRefcount);

	//atomically increment the refcount. threadsafe
	void incrementRefcount();

	//atomically decrement the refcount. if the refcount goes to zero,
	//destroy the value
	void decrementRefcount();

	LoadCheckResult attemptToLoadValues(
							VectorDataManager* inVDM,
							int64_t lowIndex,
							int64_t highIndex
							);

	BigVectorHandle* bigvecHandleForSlot(long slot) const
		{
		return mBigVectorHandleSlots[slot];
		}

	void unmapBigVectorSlot(long slot);

	void collapsePageletIfVeryFragmented(VectorDataManager* inVDM);

	ForaValueArray* unpagedValues() const
		{
		return mUnpagedValues;
		}

	bool isWriteable() const
		{
		return mIsWriteable;
		}

	void markUnwriteable()
		{
		mIsWriteable = false;
		}

	const Fora::PageletTreePtr& pageletTree() const
		{
		return mPageletTreePtr;
		}

	const boost::shared_ptr<Fora::Pagelet>& unpagedValuesPagelet() const
		{
		return mUnpagedValuesPagelet;
		}

	int64_t unpagedAndPageletTreeValueCount() const;

	int64_t pageletTreeValueCount() const;

	int64_t unpagedValueCount() const;

	Fora::BigVectorId pagedValuesIdentity() const
		{
		return mBigVectorId;
		}

	int64_t pagedValueCount() const;

	int64_t pagedAndPageletTreeValueCount() const
		{
		return mPagedAndPageletTreeValueCount;
		}

	hash_type vectorHash() const
		{
		return mVectorHash;
		}

	MemoryPool* owningMemoryPool() const
		{
		return mOwningMemoryPool;
		}

	bool hasReferencesToPagedData() const;

	VectorHandlePtr paged(MemoryPool* inPool, VectorDataManager* inVDM);

	void valueAppendedToUnpagedData()
		{
		mSize++;
		}

	void valueAppendedToUnpagedData(int64_t count)
		{
		mSize += count;
		}

	bool isEmptyOrVectorOfUint8() const;

	void makeSpaceForNewUnpagedValues(VectorDataManager* inVDM) const;

	void moveUnpagedValueArrayIntoPagelet(VectorDataManager* inVDM) const;

	bool visitAnyValuesPresentInVdm(
			VectorDataManager* inVDM,
			boost::function2<void, ForaValueArray*, IntegerSequence> visitor,
			IntegerSequence subsequence
			);

	bool visitAnyVectorHandleComponents(
			boost::function2<bool, Fora::BigVectorId, IntegerSequence> pagedDataVisitor,
			boost::function2<bool, ForaValueArray*, IntegerSequence> pageletAndUnpagedValuesVisitor,
			IntegerSequence subsequence
			);

	//collapse 'valuesUsed' of the values in our pagelet and unpaged values array into a new array
	//we may re-use portions of our own PageletTree. If the ForaValueArray is populated, it will
	//be owned by the new context. if 'allowUnpagedValuesInResult' is false, then the FVA* will be
	//null.
	pair<Fora::PageletTreePtr, ForaValueArray*> collapsePageletTreeAndUnpagedValuesTree(
														int64_t valuesUsed,
														VectorDataManager* inVDM,
														MemoryPool* inPool,
														bool allowUnpagedValuesInResult
														);

	void validateInternalInvariants();

	const HomogenousVectorStash& getHomogenousVectorStash() const
		{
		return mHomogenousVectorStash;
		}

private:
	friend ostream& operator<<(ostream& s, VectorHandle* handle);

	AO_t mRefcount;

	mutable Fora::PageletTreePtr mPageletTreePtr;

	mutable ForaValueArray* mUnpagedValues;

	mutable uint64_t mPagedAndPageletTreeValueCount;

	MemoryPool* mOwningMemoryPool;	//who owns this VectorHandle?

	uint64_t mSize;

	uword_t mIsWriteable;	//is the VectorHandle's data is unpaged and contained within
									//an execution context (e.g. not within a MemoryPool)?

	uword_t mValidityFlag;	//used by system internally to track valid vectors.

	BigVectorHandle* mBigVectorHandleSlots[kMaxBigVectorHandles];

	hash_type mVectorHash;

	//for small vectors, an HVS we can just read from
	HomogenousVectorStash mHomogenousVectorStash;

	Fora::BigVectorId mBigVectorId;

	boost::shared_ptr<Fora::Pagelet> mUnpagedValuesPagelet;
};

ostream&	operator<<(ostream& s, VectorHandle* vd);
ostream&	operator<<(ostream& s, VectorHandlePtr vd);

}
}


