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
#include "MemoizableDuringSerialization.hpp"
#include "../../core/Logging.hpp"


namespace Fora {

namespace MemoizableDuringSerialization {

MemoStorageBaseRegistry::MemoStorageBaseRegistry() : 
		mIsFrozen(false)
	{
	}
	
MemoStorageBaseRegistry& MemoStorageBaseRegistry::singleton()
	{
	static MemoStorageBaseRegistry registry;

	return registry;
	}

void MemoStorageBaseRegistry::registerFactory(const char* inType, boost::function0<MemoStorageBase*> inFactory)
	{
	boost::mutex::scoped_lock lock(mMutex);

	lassert(!mIsFrozen);

	mFactories[inType] = inFactory;

	mNamesToTypeinfos[inType] = inType;
	}

uint32_t MemoStorageBaseRegistry::typenameToIndex(const char* inType)
	{
	boost::mutex::scoped_lock lock(mMutex);

	if (!mIsFrozen)
		freeze_();

	auto it = mTypeNameIndices.find(inType);

	lassert(it != mTypeNameIndices.end());

	return it->second;
	}

const char* MemoStorageBaseRegistry::indexToTypename(uint32_t inIndex)
	{
	boost::mutex::scoped_lock lock(mMutex);

	if (!mIsFrozen)
		freeze_();

	lassert(mTypeinfos.size() > inIndex);

	return mTypeinfos[inIndex];
	}

namespace {

class StrcmpLess {
public:
	bool operator()(const char* l1, const char* l2) const
		{
		return strcmp(l1, l2) < 0;
		}
};

};

void MemoStorageBaseRegistry::freeze_()
	{
	lassert(!mIsFrozen);

	std::set<const char*> names;
	
	for (auto it = mFactories.begin(); it != mFactories.end(); it++)
		names.insert(it->first);

	for (auto it = names.begin(); it != names.end(); it++)
		{
		uint32_t index = mTypeNameIndices.size();
		mTypeNameIndices[*it] = index;
		mTypeinfos.push_back(mNamesToTypeinfos[*it]);
		}

	mIsFrozen = true;
	}
	
MemoStorageBase* MemoStorageBaseRegistry::create(const char* inType)
	{
	boost::mutex::scoped_lock lock(mMutex);

	auto it = mFactories.find(inType); 

	if (it == mFactories.end())
		return 0;

	return it->second();
	}

}
}

