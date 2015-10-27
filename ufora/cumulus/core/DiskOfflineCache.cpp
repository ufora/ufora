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
#include <fcntl.h>

#include "DiskOfflineCache.hpp"
#include "../../core/math/Hash.hpp"
#include "../../core/Logging.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/math/Nullable.hpp"
#include "../../core/Memory.hpp"
#include "../../FORA/Serialization/SerializedObject.hpp"
#include "../../core/serialization/IFileDescriptorProtocol.hpp"
#include "../../core/serialization/OFileDescriptorProtocol.hpp"
#include <string>
#include <unistd.h>

namespace Cumulus {


DiskOfflineCache::DiskOfflineCache(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
			std::string basePath, 
			uint64_t maxCacheSize, 
			uint64_t maxCacheItemCount
			) :
		OfflineCache(inCallbackScheduler),
		mCacheSize(0), 
		mCacheItemCount(0),
		mMaxCacheSize(maxCacheSize),
		mMaxCacheItemCount(maxCacheItemCount),
		mCurRandomHash(1),
		mTotalBytesDumped(0),
		mTotalFilesDumped(0),
		mTotalBytesLoaded(0)
	{
	lassert(mMaxCacheItemCount > 0);
	lassert(mMaxCacheSize > 0);

	mBasePath = boost::filesystem::path(basePath);
	if (!boost::filesystem::exists(mBasePath))
		boost::filesystem::create_directories(mBasePath);

	for (boost::filesystem::directory_iterator dIt(mBasePath); 
			dIt != boost::filesystem::directory_iterator(); ++dIt) 
		{
		lassert_dump(false, "Expected DiskOfflineCache to be empty.");
		}
	}

DiskOfflineCache::DiskOfflineCache(
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
			boost::filesystem::path basePath, 
			uint64_t maxCacheSize, 
			uint64_t maxCacheItemCount
			) :
		OfflineCache(inCallbackScheduler),
		mCacheSize(0), 
		mCacheItemCount(0),
		mMaxCacheSize(maxCacheSize),
		mMaxCacheItemCount(maxCacheItemCount),
		mCurRandomHash(1),
		mTotalBytesDumped(0),
		mTotalFilesDumped(0),
		mTotalBytesLoaded(0),
        mBasePath(basePath)
	{
	lassert(mMaxCacheItemCount > 0);
	lassert(mMaxCacheSize > 0);
	
	if (!boost::filesystem::exists(mBasePath))
		boost::filesystem::create_directories(mBasePath);

	for (boost::filesystem::directory_iterator dIt(mBasePath); 
			dIt != boost::filesystem::directory_iterator(); ++dIt) 
		{
		lassert_dump(false, "Expected DiskOfflineCache to be empty.");
		}
	}

uint64_t DiskOfflineCache::getTotalBytesLoaded(void) const
	{
	return mTotalBytesLoaded;
	}

uint64_t DiskOfflineCache::getCacheSizeUsedBytes(void) const
	{
	return mCacheSize;
	}

uint64_t DiskOfflineCache::getCacheItemCount(void) const
	{
	return mCacheItemCount;
	}

uint64_t DiskOfflineCache::getCacheBytesDropped(void) const
	{
	return mTotalBytesDumped;
	}
	
uint64_t DiskOfflineCache::getCacheItemsDropped(void) const
	{
	return mTotalFilesDumped;
	}

void DiskOfflineCache::store(		
				const Fora::PageId& inDataID,
				const PolymorphicSharedPtr<SerializedObject>& inSerializedData
				) 
	{
		{
		boost::recursive_mutex::scoped_lock		lock(mMutex);

		LOG_DEBUG << "DOC " << this << " storing " << inDataID;

		if (mPagesToDropAfterIO.find(inDataID) != mPagesToDropAfterIO.end())
			{
			LOG_DEBUG << "DOC " << this << " scheduling " << inDataID << " to drop after IO";
			mPagesToDropAfterIO.erase(inDataID);
			return;
			}

		if (mPagesHeld.find(inDataID) != mPagesHeld.end())
			{
			LOG_WARN << "Disk Cache already has data for " << inDataID;
			return;
			}

		if (mPagesBeingWritten.find(inDataID) != mPagesBeingWritten.end())
			{
			LOG_WARN << "Disk Cache is already writing " << inDataID;
			return;
			}

		mPagesBeingWritten[inDataID] = inSerializedData;
		}

	boost::filesystem::path datPath(pathFor(inDataID));

	lassert_dump(!boost::filesystem::exists(datPath), datPath);

	int fd = open(datPath.string().c_str(), O_DIRECT | O_CREAT | O_WRONLY, S_IRWXU);

	lassert_dump(fd != -1, "failed to open " << datPath.string() << ": " << strerror(errno));

	int64_t bytesWritten;

		{
		OFileDescriptorProtocol protocol(
			fd, 
			512,
			1024 * 1024 * 20, 
			OFileDescriptorProtocol::CloseOnDestroy::True
			);

			{
			OBinaryStream stream(protocol);
		
			SerializedObjectFlattener::flattenOnce(stream, inSerializedData);
			}

		LOG_INFO << "Disk cache stored " 
			<< protocol.position() / 1024 / 1024.0 << " MB. "
			<< " Holding " << mCacheSize / 1024.0 / 1024.0 
			<< " of a maximum " << mMaxCacheSize / 1024.0 / 1024.0 << " MB and "
			<< mCacheItemCount << " of " << mMaxCacheItemCount << " items."
			<< " path = " << datPath.string()
			;

		bytesWritten = protocol.position();
		}

		{
		boost::recursive_mutex::scoped_lock		lock(mMutex);

		mCacheSize += bytesWritten;
		mCacheItemCount += 1;

		mFileSizes.insert(make_pair(datPath.filename().string(), bytesWritten));
		mPageIDs[datPath.filename().string()] = inDataID;
		
		LOG_DEBUG << "DOC " << this << " finished storing " << inDataID;

		mPagesHeld.insert(inDataID);
		mPagesBeingWritten.erase(inDataID);

		if (mPagesToDropAfterIO.find(inDataID) != mPagesToDropAfterIO.end())
			{
			LOG_DEBUG << "DOC " << this << " dropping " << inDataID 
				<< " because it was scheduled for dropAfterIO.";

			mPagesToDropAfterIO.erase(inDataID);
			drop(inDataID);
			}

		dropExcessCacheItemsExcluding(inDataID);
		}
	}		

bool DiskOfflineCache::alreadyExists(const Fora::PageId& inID)
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);

	if (mPagesHeld.find(inID) != mPagesHeld.end() || 
				mPagesBeingWritten.find(inID) != mPagesBeingWritten.end())
		return true;

	return false;
	}


PolymorphicSharedPtr<SerializedObject> DiskOfflineCache::loadIfExists(const Fora::PageId& inID)
	{
		{
		boost::recursive_mutex::scoped_lock		lock(mMutex);

		LOG_DEBUG << "DOC " << this << " loading " << inID << " if it exists";

		if (mPagesBeingWritten.find(inID) != mPagesBeingWritten.end())
			{
			LOG_DEBUG << "DOC " << this << " returning " << inID << " because it is already being written";
			return mPagesBeingWritten[inID];
			}

		if (mPagesHeld.find(inID) == mPagesHeld.end())
			{
			LOG_DEBUG << "DOC " << this << " returning null for " << inID << " because it's not held";

			return PolymorphicSharedPtr<SerializedObject>();
			}

		if (mPagesBeingRead.find(inID) != mPagesBeingRead.end())
			{
			boost::shared_ptr<Queue<PolymorphicSharedPtr<SerializedObject> > > queuePtr(
					new Queue<PolymorphicSharedPtr<SerializedObject> >()
					);
				
			mQueuesForBlockedReads[inID].push_back(queuePtr);

			LOG_DEBUG << "DOC " << this << " waiting for read of " << inID << ".";

			lock.unlock();

			return queuePtr->get();
			}
		else
			mPagesBeingRead.insert(inID);
		}

	boost::filesystem::path datPath(pathFor(inID));

	lassert_dump(boost::filesystem::exists(datPath), datPath);

	int fd = open(datPath.string().c_str(), O_DIRECT | O_RDONLY, S_IRWXU);

	lassert_dump(fd != -1, "failed to open " << datPath.string() << ": " << strerror(errno));
	
	IFileDescriptorProtocol protocol(
		fd, 
		512, 
		20 * 1024 * 1024, 
		IFileDescriptorProtocol::CloseOnDestroy::True
		);

	PolymorphicSharedPtr<SerializedObject> result;
	
	uint64_t origMem = Ufora::Memory::getTotalBytesAllocated();

		{
		IBinaryStream stream(protocol);
		
		result = SerializedObjectInflater::inflateOnce(stream);
		}
	
	lassert(result);

	LOG_INFO << "Disk cache loaded " 
		<< protocol.position() / 1024.0 / 1024.0 << " MB from " 
		<< datPath.filename().string() << ". ram = " << origMem / 1024 / 1024.0 << " -> "
		<< Ufora::Memory::getTotalBytesAllocated() / 1024 / 1024.0
		;

	mTotalBytesLoaded += protocol.position();

		{
		boost::recursive_mutex::scoped_lock		lock(mMutex);

		LOG_DEBUG << "DOC " << this << " finished read of " << inID << ".";

		mPagesBeingRead.erase(inID);

		for (auto queuePtr: mQueuesForBlockedReads[inID])
			queuePtr->write(result);

		mQueuesForBlockedReads.erase(inID);

		if (mPagesToDropAfterIO.find(inID) != mPagesToDropAfterIO.end())
			{
			LOG_DEBUG << "DOC " << this << " dropping " << inID << " after IO.";

			mPagesToDropAfterIO.erase(inID);
			drop(inID);
			}
		}

	return result;
	}


boost::filesystem::path  DiskOfflineCache::pathFor(const Fora::PageId& inID)
	{
	// the /= operator appends the native directory seperator
	return mBasePath / filenameFor(inID);	
	}

std::string  DiskOfflineCache::filenameFor(const Fora::PageId& inID)
	{
	return hashToString(inID.guid()) + "_" + boost::lexical_cast<string>(inID.bytecount());
	}

void DiskOfflineCache::drop(const Fora::PageId& inID)
	{
	boost::recursive_mutex::scoped_lock lock(mMutex);

	LOG_DEBUG << "DOC " << this << " dropping " << inID;

	if (mPagesBeingWritten.find(inID) != mPagesBeingWritten.end() || 
				mPagesBeingRead.find(inID) != mPagesBeingRead.end())
		{
		LOG_DEBUG << "DOC " << this << " deferring drop of " << inID << " until after IO.";

		mPagesToDropAfterIO.insert(inID);
		return;
		}

	if (mPagesHeld.find(inID) == mPagesHeld.end())
		{
		LOG_DEBUG << "DOC " << this << " can't drop " << inID << " because it's not held.";
		return;
		}

	if (mPagesToDropAfterIO.find(inID) != mPagesToDropAfterIO.end())
		{
		LOG_DEBUG << "DOC " << this << " deferring drop of " << inID 
			<< " because it's already scheduled to drop after IO";

		return;
		}

	mPagesHeld.erase(inID);
	
	dropItemByName_(filenameFor(inID));	
	}

void	DiskOfflineCache::dropExcessCacheItemsExcluding(Fora::PageId itemToExclude)
	{
	boost::recursive_mutex::scoped_lock		lock(mMutex);
	
	long failedPasses = 0;

	while (mCacheItemCount > mMaxCacheItemCount || mCacheSize > mMaxCacheSize)
		{
		Fora::PageId cacheItemToDelete = pickARandomCacheItem();

		if (cacheItemToDelete != itemToExclude && 
				mPagesToDropAfterIO.find(cacheItemToDelete) == mPagesToDropAfterIO.end() && 
				mPagesBeingWritten.find(cacheItemToDelete) == mPagesBeingWritten.end() && 
				mPagesBeingRead.find(cacheItemToDelete) == mPagesBeingRead.end()
				)
			{
			LOG_DEBUG << "DOC " << this << " dropping " << cacheItemToDelete
				<< " beccause the cache is full.";

			drop(cacheItemToDelete);

			failedPasses = 0;
			}
		else
			{
			failedPasses++;
			LOG_DEBUG << "DOC " << this << " not dropping " << cacheItemToDelete
				<< " beccause it's unavailable to drop.";
			}

		if (failedPasses > 100)
			{
			LOG_CRITICAL << "DiskOfflineCache failed to dump anything despite having "
				<< "too much data. We have "
				<< mCacheItemCount << " items with " << mCacheSize << " bytes. our max is "
				<< mMaxCacheItemCount << " items and " << mMaxCacheSize << " bytes."
				;
			lassert(false);
			}
		}
	}

void DiskOfflineCache::dropItemByName_(std::string cacheItemToDelete)
	{
	if (mFileSizes.find(cacheItemToDelete) == mFileSizes.end())
		{
		LOG_WARN << "DiskOfflineCache tried to drop non-held file " << cacheItemToDelete;
		return;
		}

	if (mPageIDs.find(cacheItemToDelete) == mPageIDs.end())
		{
		LOG_WARN << "DiskOfflineCache dropping an unknown file " << cacheItemToDelete 
			<< ". probably this was already in the cache when we started.";
		return;
		}
	else
		{
		onPageDropped().broadcast(mPageIDs[cacheItemToDelete]);
		mPageIDs.erase(cacheItemToDelete);
		}

	LOG_INFO << "DiskOfflineCache dropping " << cacheItemToDelete 
		<< " with " << mFileSizes[cacheItemToDelete] << " bytes. " 
		<< " Holding " << mCacheSize / 1024.0 / 1024.0 
		<< " of a maximum " << mMaxCacheSize / 1024.0 / 1024.0 << " MB and "
		<< mCacheItemCount << " of " << mMaxCacheItemCount << " items."
		;
	
	if (!boost::filesystem::remove(mBasePath / cacheItemToDelete))
		throw standardLogicErrorWithStacktrace(
			"Cache File " + cacheItemToDelete + " not deleted successfully."
			);
	
	mTotalFilesDumped += 1;
	mTotalBytesDumped += mFileSizes[cacheItemToDelete];

	mCacheItemCount -= 1;
	mCacheSize -= mFileSizes[cacheItemToDelete];

	mFileSizes.erase(cacheItemToDelete);
	}

Fora::PageId DiskOfflineCache::pickARandomCacheItem()
	{
	boost::recursive_mutex::scoped_lock		lock(mMutex);
	
	lassert(mPageIDs.size());

	if (mPageIDs.size() == 1)
		return mPageIDs.begin()->second;
	
	mCurRandomHash = mCurRandomHash + hash_type(1);
	std::string candidateFilename = hashToString(mCurRandomHash);

	std::map<std::string, Fora::PageId>::iterator it = 
		mPageIDs.lower_bound(candidateFilename);
	
	if (it == mPageIDs.end())
		it = mPageIDs.begin();
	
	return it->second;
	}




} // namespace cumulus

