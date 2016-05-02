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
#include "MemoryPool.hpp"
#include "ShareableMemoryBlocks.hppml"
#include "../../core/StringUtil.hpp"
#include "../../core/Memory.hpp"
#include "../../core/Logging.hpp"
#include "../VectorDataManager/Pagelet.hppml"
#include <boost/unordered_map.hpp>
#include <boost/thread.hpp>
#include "../../core/lassert.hpp"

#include "../../core/threading/Trigger.hppml"

//A simple malloc wrapper for the free store.
class TrackingFreeStoreMallocPool : public MemoryPool {
public:
	TrackingFreeStoreMallocPool() :
			MemoryPool(MemoryPool::MemoryPoolType::FreeStore)
		{
		}

	std::string stringRepresentation()
		{
		return "TrackingFreeStore()";
		}

	Fora::ShareableMemoryBlockHandle convertPointerToShareableMemoryBlock(uint8_t* inBytes, int64_t bytes)
		{
		return Fora::ShareableMemoryBlockHandle();
		}

	virtual uint8_t* allocate(size_t inBytes)
		{
		uint8_t* tr = (uint8_t*)malloc(inBytes);

		boost::mutex::scoped_lock lock(mMutex);
		mByteCount[tr] = inBytes;

		return tr;
		}

	void vectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage,
						boost::shared_ptr<Ufora::threading::Trigger> mappedPageWantsUnmapped
						)
		{
		lassert_dump(false, "this should never happen. Mapping vectors in the free-store can't work");
		}

	bool isVectorPageMapped(boost::shared_ptr<VectorPage> mappedPage)
		{
		return false;
		}

	virtual void free(uint8_t* inBytes)
		{
		boost::mutex::scoped_lock lock(mMutex);
		lassert(mByteCount.find(inBytes) != mByteCount.end());
		mByteCount.erase(inBytes);

		::free(inBytes);
		}

	virtual uint8_t* realloc(uint8_t* inBytes, uword_t inNewBytes)
		{
		boost::mutex::scoped_lock lock(mMutex);
		lassert(mByteCount.find(inBytes) != mByteCount.end() || !inBytes);
		mByteCount.erase(inBytes);

		uint8_t* tr = (uint8_t*) ::realloc(inBytes, inNewBytes);

		mByteCount[tr] = inNewBytes;

		return tr;
		}

	virtual size_t totalBytesAllocated() const
		{
		return 0;
		}

	virtual size_t totalBytesAllocatedFromOSExcludingPagelets() const
		{
		return 0;
		}

	virtual size_t totalBytesAllocatedFromOS() const
		{
		return 0;
		}

	size_t totalBytesFromOSHeldInPagelets() const
		{
		return 0;
		}

	virtual bool permitAllocation(size_t inBytes)
		{
		return true;
		}

	boost::mutex mMutex;
	boost::unordered_map<uint8_t*, uword_t> mByteCount;
};

class FreeStoreMallocPool : public MemoryPool {
public:
	const static bool kTrackPageletsInFreeStore = false;

	FreeStoreMallocPool() :
			MemoryPool(MemoryPool::MemoryPoolType::FreeStore),
			mBytesInPagelets(0)
		{
		}

	std::string stringRepresentation()
		{
		return "FreeStore()";
		}

	bool isVectorPageMapped(boost::shared_ptr<VectorPage> mappedPage)
		{
		return false;
		}

	void pageletIsHeld(boost::shared_ptr<Fora::Pagelet> inPagelet)
		{
		if (!kTrackPageletsInFreeStore)
			return;

		boost::mutex::scoped_lock lock(mPageletRefcountMutex);

		incref_(inPagelet);

		for (auto pageletAndRefcount: inPagelet->getHeldPagelets())
			incref_(pageletAndRefcount.first);
		}

	void pageletIsNoLongerHeld(boost::shared_ptr<Fora::Pagelet> inPagelet)
		{
		if (!kTrackPageletsInFreeStore)
			return;

		boost::mutex::scoped_lock lock(mPageletRefcountMutex);

		decref_(inPagelet);

		for (auto pageletAndRefcount: inPagelet->getHeldPagelets())
			decref_(pageletAndRefcount.first);
		}

	Fora::ShareableMemoryBlockHandle convertPointerToShareableMemoryBlock(uint8_t* inBytes, int64_t bytes)
		{
		long shareableBlockIndex = ((size_t)inBytes) % kSmallPrime;

		boost::upgrade_lock<boost::shared_mutex> lock(
			mShareableMemoryBlockMutexes[shareableBlockIndex]
			);

		return mShareableMemoryBlocks[shareableBlockIndex].getShareableMemoryBlockHandle(inBytes);
		}

	uint8_t* importShareableMemoryBlock(const Fora::ShareableMemoryBlockHandle& inHandle)
		{
		if (inHandle.isEmpty())
			return nullptr;

		long shareableBlockIndex = ((size_t)inHandle.getBaseAddress()) % kSmallPrime;

		boost::upgrade_lock<boost::shared_mutex> lock(
			mShareableMemoryBlockMutexes[shareableBlockIndex]
			);

		boost::upgrade_to_unique_lock<boost::shared_mutex> uniqueLock(lock);

		mShareableMemoryBlocks[shareableBlockIndex].increfShareableMemoryBlockAndReturnIsNew(inHandle);

		return inHandle.getBaseAddress();
		}

	virtual uint8_t* allocate(size_t inBytes)
		{
		return (uint8_t*)malloc(inBytes);
		}

	virtual void free(uint8_t* inBytes)
		{
		if (!Fora::ShareableMemoryBlock::isValidBaseAddress(inBytes))
			{
			::free(inBytes);
			return;
			}

		long shareableBlockIndex = ((size_t)inBytes) % kSmallPrime;

		boost::upgrade_lock<boost::shared_mutex> lock(
			mShareableMemoryBlockMutexes[shareableBlockIndex]
			);

		if (mShareableMemoryBlocks[shareableBlockIndex].hasShareableMemoryBlockHandle(inBytes))
			{
			boost::upgrade_to_unique_lock<boost::shared_mutex> uniqueLock(lock);

			mShareableMemoryBlocks[shareableBlockIndex].decrefSharedMemoryBlock(inBytes);
			}
		else
			::free(inBytes);
		}

	virtual uint8_t* realloc(uint8_t* inBytes, uword_t inNewBytes)
		{
		return (uint8_t*) ::realloc(inBytes, inNewBytes);
		}

	virtual size_t totalBytesAllocatedFromOSExcludingPagelets() const
		{
		return 0;
		}

	virtual size_t totalBytesAllocated() const
		{
		return 0;
		}

	virtual size_t totalBytesAllocatedFromOS() const
		{
		return 0;
		}

	size_t totalBytesFromOSHeldInPagelets() const
		{
		return 0;
		}

	virtual bool permitAllocation(size_t inBytes)
		{
		return true;
		}

	void vectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage,
						boost::shared_ptr<Ufora::threading::Trigger> mappedPageWantsUnmapped
						)
		{
		lassert_dump(false, "this should never happen. Mapping vectors in the free-store can't work");
		}

private:
	void incref_(boost::shared_ptr<Fora::Pagelet> p)
		{
		mPageletRefcounts[p]++;
		if (mPageletRefcounts[p] == 1)
			{
			mBytesInPagelets += p->totalBytesAllocatedFromOS();

			if (mBytesInPagelets / 1024 / 1024 / 100 !=
					(mBytesInPagelets - p->totalBytesAllocatedFromOS()) / 1024 / 1024 / 100)
				LOG_INFO << mBytesInPagelets / 1024 / 1024.0 << " MB of pagelets in the free store.";
			}
		}

	void decref_(boost::shared_ptr<Fora::Pagelet> p)
		{
		mPageletRefcounts[p]--;
		if (mPageletRefcounts[p] == 0)
			{
			mBytesInPagelets -= p->totalBytesAllocatedFromOS();
			mPageletRefcounts.erase(p);

			if (mBytesInPagelets / 1024 / 1024 / 100 !=
					(mBytesInPagelets + p->totalBytesAllocatedFromOS()) / 1024 / 1024 / 100)
				LOG_INFO << mBytesInPagelets / 1024 / 1024.0 << " MB of pagelets in the free store.";
			}
		}

	const static long kSmallPrime = 41;

	boost::shared_mutex mShareableMemoryBlockMutexes[kSmallPrime];

	Fora::ShareableMemoryBlocks mShareableMemoryBlocks[kSmallPrime];

	boost::mutex mPageletRefcountMutex;

	size_t mBytesInPagelets;

	std::map<boost::shared_ptr<Fora::Pagelet>, long> mPageletRefcounts;

	std::map<boost::shared_ptr<Fora::Pagelet>, std::vector<std::string> > mPageletRefcountSources;
};


MemoryPool* MemoryPool::getFreeStorePool()
	{
	static MemoryPool* pool = new FreeStoreMallocPool();

	return pool;
	}

std::ostream& operator<<(std::ostream& s, MemoryPool* pool)
	{
	if (!pool)
		s << "MemoryPool(<null>)";
	else
		s << pool->stringRepresentation();

	return s;
	}

