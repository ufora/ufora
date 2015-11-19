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

#include "../../FORA/VectorDataManager/OfflineCache.hpp"
#include "../../FORA/Vector/VectorDataID.hppml"
#include "../../FORA/Serialization/SerializedObject.hpp"
#include "../../FORA/Serialization/SerializedObjectFlattener.hpp"
#include <stdint.h>
#include "../../core/Logging.hpp"

namespace Cumulus {

//implements a very simple OfflineCache object that just holds everything
//in RAM.  The cache has a maximum byte size and drops random elements
//(sorted by affinity) until it has enough space to hold the current item
class SimpleOfflineCache : public OfflineCache {
public:
	typedef PolymorphicSharedPtr<SimpleOfflineCache, OfflineCache::pointer_type> pointer_type;

	SimpleOfflineCache(
					PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
					uint64_t inMaxBytes
					) :
			OfflineCache(inCallbackScheduler),
			mBytes(0),
			mTotalReloads(0),
			mMaxBytes(inMaxBytes),
			mEventId(0)
		{
		}

	//stores a value in the cache.
	void	store(	const Fora::PageId& page,
					const PolymorphicSharedPtr<SerializedObject>& inData
					)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mPageTouchSequence.set(page, mEventId++);
		
		PolymorphicSharedPtr<NoncontiguousByteBlock> stringData = 
			SerializedObjectFlattener::flattenOnce(inData);

		if (mData.find(page) != mData.end())
			mBytes -= mData[page]->totalByteCount();
		
		mData[page] = stringData;
		
		mBytes += mData[page]->totalByteCount();
		
		while (mBytes >= mMaxBytes)
			{
			//drop oldest pages first, by checking in mPageTouchSequence
			//nonsensical to have mBytes > 0 and nothing in mPageTouchSequence
			lassert(mPageTouchSequence.size());

			Fora::PageId dropCandidate = *mPageTouchSequence.getKeys(mPageTouchSequence.lowestValue()).begin();

			lassert(mData.find(dropCandidate) != mData.end());

			drop(dropCandidate);
			}
		}
	
	//checks whether a value for the given cache key definitely already
	//exists.
	bool	alreadyExists(const Fora::PageId& inPage)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (mData.find(inPage) != mData.end())
			mPageTouchSequence.set(inPage, mEventId++);

		return mData.find(inPage) != mData.end();
		}
	
	//return the data if we have it
	PolymorphicSharedPtr<SerializedObject> loadIfExists(const Fora::PageId& page)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (mData.find(page) != mData.end())
			{
			mPageTouchSequence.set(page, mEventId++);

			mTotalReloads += mData[page]->totalByteCount();
			
			return SerializedObjectInflater::inflateOnce(mData[page]);
			}
		return PolymorphicSharedPtr<SerializedObject>();
		}

	static uint64_t 	totalBytesStatic(SimpleOfflineCache::pointer_type& self)
		{
		return self->totalBytes();
		}				
	static uint64_t 	totalBytesLoadedStatic(SimpleOfflineCache::pointer_type& self)
		{
		return self->totalBytesLoaded();
		}				

	uint64_t 	totalBytes(void)
		{
		return mBytes;
		}
	uint64_t 	totalBytesLoaded(void)
		{
		return mTotalReloads;
		}
	static void dropCacheTermStatic(
						SimpleOfflineCache::pointer_type& self, 
						const Fora::PageId& source
						)
		{
		self->drop(source);
		}

	void drop(const Fora::PageId& page)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);
		
		mPageTouchSequence.discard(page);

		if (!mData.size())
			return;
		
		if (mData.find(page) != mData.end())
			{
			LOG_INFO << "SimpleOfflineCache dropping " << prettyPrintString(page);

			onPageDropped().broadcast(page);
			
			mItemsDropped++;

			mBytesDropped += mData[page]->totalByteCount();
			
			mBytes -= mData[page]->totalByteCount();
			mData.erase(page);
			}
		}
	uint64_t getCacheSizeUsedBytes(void) const
		{
		return mBytes;
		}
	uint64_t getCacheItemCount(void) const
		{
		return mData.size();
		}
	uint64_t getCacheBytesDropped(void) const
		{
		return mBytesDropped;
		}
	uint64_t getCacheItemsDropped(void) const
		{
		return mItemsDropped;
		}
	
private:
	boost::recursive_mutex mMutex;

	map<Fora::PageId, PolymorphicSharedPtr<NoncontiguousByteBlock> >	mData;

	MapWithIndex<Fora::PageId, int64_t> mPageTouchSequence;

	int64_t mEventId;

	uint64_t mBytes;
	uint64_t mBytesDropped;
	uint64_t mItemsDropped;

	uint64_t mTotalReloads;
	uint64_t mMaxBytes;
};

}


