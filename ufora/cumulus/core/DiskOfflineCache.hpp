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

#include "../../core/math/Hash.hpp"
#include "../../core/IntegerTypes.hpp"
#include "../../core/threading/Queue.hpp"
#include "../../FORA/Serialization/SerializedObjectFlattener.hpp"

#include "../../FORA/VectorDataManager/OfflineCache.hpp"
#include <boost/filesystem.hpp>
#include <string>

namespace Cumulus {

/*******
 * Disk implementation of OfflineCache interface
 *********/


class DiskOfflineCache : public OfflineCache {
public:
	typedef PolymorphicSharedPtr<DiskOfflineCache, OfflineCache::pointer_type> pointer_type;

	DiskOfflineCache(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
			std::string basePath,
			uint64_t maxCacheSize,
			uint64_t maxCacheItemCount
			);

	DiskOfflineCache(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
			boost::filesystem::path basePath,
			uint64_t maxCacheSize,
			uint64_t maxCacheItemCount
			);

	//stores a value in the cache.
	void store(		const Fora::PageId& inID,
					const PolymorphicSharedPtr<SerializedObject>& inData
					);

	void drop(const Fora::PageId& inID);

	//checks whether a value for the given cache key definitely already
	//exists.
	bool alreadyExists(const Fora::PageId& inID);

	uint64_t getCacheSizeUsedBytes(void) const;
	uint64_t getCacheItemCount(void) const;
	uint64_t getCacheBytesDropped(void) const;
	uint64_t getCacheItemsDropped(void) const;

	uint64_t getTotalBytesLoaded(void) const;

	//checks whether a value for the given cache key definitely already
	//exists.
	PolymorphicSharedPtr<SerializedObject> loadIfExists(const Fora::PageId& inID);

private:
	boost::recursive_mutex			mMutex;

	// dropItemByName_ must be called with mMutex held
	void dropItemByName_(std::string cacheItemToDelete);

	boost::filesystem::path pathFor(const Fora::PageId& inID);

	std::string filenameFor(const Fora::PageId& inID);

	void dropExcessCacheItemsExcluding(Fora::PageId itemName);

	Fora::PageId pickARandomCacheItem();

	boost::filesystem::path	mBasePath;

    std::map<std::string, uint64_t> mFileSizes;

    std::map<std::string, Fora::PageId> mPageIDs;

    std::set<Fora::PageId> mPagesHeld;

    std::map<Fora::PageId, PolymorphicSharedPtr<SerializedObject> > mPagesBeingWritten;

    std::set<Fora::PageId> mPagesBeingRead;

    std::map<Fora::PageId,
    	std::vector<
    		boost::shared_ptr<
    			Queue<PolymorphicSharedPtr<SerializedObject> >
    			>
    		>
    	> mQueuesForBlockedReads;

    std::set<Fora::PageId> mPagesToDropAfterIO;

    uint64_t mCacheSize;

    uint64_t mCacheItemCount;

    uint64_t mTotalBytesDumped;

    uint64_t mTotalBytesLoaded;

    uint64_t mTotalFilesDumped;

    uint64_t mMaxCacheSize;

    uint64_t mMaxCacheItemCount;

    hash_type mCurRandomHash;
};

}

