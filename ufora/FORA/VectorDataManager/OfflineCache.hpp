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
#include "../../core/PolymorphicSharedPtr.hpp"
#include "../Vector/VectorDataID.hppml"
#include "../../core/EventBroadcaster.hpp"
#include <string>


class SerializedObject;

/************
Base class used to push items into some long-term storage. Clients may not
assume that the data is retained perfectly.
************/

class OfflineCache : public PolymorphicSharedPtrBase<OfflineCache> {
public:
		typedef PolymorphicSharedPtr<OfflineCache> pointer_type;
                OfflineCache(PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler) : 
                    mOnPageDropped(inCallbackScheduler)
                    {}
		
		virtual ~OfflineCache() {};

		//stores a value in the cache.
		virtual void	store(	const Fora::PageId& inDataID,
								const PolymorphicSharedPtr<SerializedObject>& inData
								) = 0;

		//drop a value from the cache
		virtual void drop(const Fora::PageId& inDataID) = 0;
		
		//checks whether a value for the given cache key definitely already
		//exists.
		virtual bool	alreadyExists(const Fora::PageId& inDataID) = 0;
		
		//checks whether a value for the given cache key definitely already
		//exists.
		virtual PolymorphicSharedPtr<SerializedObject>
						loadIfExists(const Fora::PageId& inDataID) = 0;
		
		
		virtual uint64_t getCacheSizeUsedBytes(void) const = 0;
		virtual uint64_t getCacheItemCount(void) const = 0;
		virtual uint64_t getCacheBytesDropped(void) const = 0;
		virtual uint64_t getCacheItemsDropped(void) const = 0;

		EventBroadcaster<Fora::PageId>& onPageDropped()
			{
			return mOnPageDropped;
			}

private:
		EventBroadcaster<Fora::PageId> mOnPageDropped;

};


