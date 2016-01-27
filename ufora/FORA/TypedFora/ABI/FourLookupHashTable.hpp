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

#include <boost/thread.hpp>
#include "../../../core/lassert.hpp"
#include "../../../core/Clock.hpp"
#include "../../../core/threading/CallbackScheduler.hppml"

namespace TypedFora {
namespace Abi {

PolymorphicSharedPtr<CallbackScheduler> fourLookupHashTableDeletionCallbackScheduler();

template<class key_type, class value_type>
class UnresizableFourLookupHashTable {
	key_type* mKeys;
	
	value_type* mValues;

	size_t mBucketCount;

	size_t mElementCount;

public:
	const static long PRIME_1 = 104729;
	const static long PRIME_2 = 15485863;
	const static long PRIME_3 = 19;
	const static long PRIME_4 = 503;

	UnresizableFourLookupHashTable(long inCount) : 
			mBucketCount(inCount),
			mElementCount(0)
		{
		mKeys = (key_type*)malloc(sizeof(key_type) * inCount);
		mValues = (value_type*)malloc(sizeof(value_type) * inCount);
		memset(mKeys, 0, sizeof(key_type) * inCount);
		memset(mValues, 0, sizeof(key_type) * inCount);
		}

	~UnresizableFourLookupHashTable()
		{
		free(mKeys);
		free(mValues);
		}

	size_t size()
		{
		return mElementCount;
		}

	size_t bucketCount()
		{
		return mBucketCount;
		}

	bool hashInto(UnresizableFourLookupHashTable& other)
		{
		for (long k = 0; k < mBucketCount; k++)
			if (mKeys[k])
				if (!other.insert(mKeys[k], mValues[k]))
					return false;
		return true;
		}

	size_t firstSlotFor(key_type k)
		{
		return (k * PRIME_1 + 1) % mBucketCount;
		}

	size_t secondSlotFor(key_type k)
		{
		return (k * PRIME_2 + 1) % mBucketCount;
		}

	size_t thirdSlotFor(key_type k)
		{
		return (k * PRIME_3 + 1) % mBucketCount;
		}

	size_t fourthSlotFor(key_type k)
		{
		return (k * PRIME_4 + 1) % mBucketCount;
		}

	key_type& keyForSlot(long slot)
		{
		return mKeys[slot];
		}

	const key_type& keyForSlot(long slot) const
		{
		return mKeys[slot];
		}

	value_type& valueForSlot(long slot)
		{
		return mValues[slot];
		}

	const value_type& valueForSlot(long slot) const
		{
		return mValues[slot];
		}

	long slotFor(key_type k)
		{
		size_t s1 = firstSlotFor(k);
		if (mKeys[s1] == k)
			return s1;
		if (mKeys[s1] == 0)
			return -1;

		size_t s2 = secondSlotFor(k);
		if (mKeys[s2] == k)
			return s2;
		if (mKeys[s2] == 0)
			return -1;

		size_t s3 = thirdSlotFor(k);
		if (mKeys[s3] == k)
			return s3;
		if (mKeys[s3] == 0)
			return -1;
		
		size_t s4 = fourthSlotFor(k);
		if (mKeys[s4] == k)
			return s4;
		if (mKeys[s4] == 0)
			return -1;

		return -1;
		}

	bool contains(key_type k)
		{
		return slotFor(k) >= 0;
		}

	value_type& getValue(key_type k)
		{
		long slot = slotFor(k);
		lassert(slot != -1);
		return mValues[slot];
		}

	bool insert(key_type k, value_type v)
		{
		size_t s1 = firstSlotFor(k);
		if (mKeys[s1] == 0)
			{
			mValues[s1] = v;
			fullMemoryBarrier();

			mKeys[s1] = k;
			mElementCount++;
			return true;
			}

		size_t s2 = secondSlotFor(k);
		if (mKeys[s2] == 0)
			{
			mValues[s2] = v;
			fullMemoryBarrier();

			mKeys[s2] = k;
			mElementCount++;
			return true;
			}

		size_t s3 = thirdSlotFor(k);
		if (mKeys[s3] == 0)
			{
			mValues[s3] = v;
			fullMemoryBarrier();
			
			mKeys[s3] = k;
			mElementCount++;
			return true;
			}

		size_t s4 = fourthSlotFor(k);
		if (mKeys[s4] == 0)
			{
			mValues[s4] = v;
			fullMemoryBarrier();
			
			mKeys[s4] = k;
			mElementCount++;
			return true;
			}

		return false;
		}
};

template<bool threadsafe>
class FourLookupHashTableMutexType;

template<>
class FourLookupHashTableMutexType<true> {
public:
	typedef boost::mutex mutex_type;

	typedef boost::mutex::scoped_lock lock_type;
};

template<>
class FourLookupHashTableMutexType<false> {
public:
	class mutex_type {};
	
	class lock_type { public: lock_type(mutex_type&) {} };
};


//A lookup table (with codegen) that takes at most 2 hash lookups.
//data types should be integers, and key_type may never be zero
template<class key_type, class value_type, bool threadsafe>
class FourLookupHashTable {
public:
	FourLookupHashTable(const FourLookupHashTable& in) : 
			mTable(new UnresizableFourLookupHashTable<key_type, value_type>(in.bucketCount()))
		{
		lassert(in.mTable->hashInto(*mTable));
		}

	FourLookupHashTable& operator=(const FourLookupHashTable& in)
		{
		delete mTable;

		mTable = new UnresizableFourLookupHashTable<key_type, value_type>(in.bucketCount());

		in.mTable->hashInto(*mTable);

		return *this;
		}

	FourLookupHashTable() : 
			mTable(new UnresizableFourLookupHashTable<key_type, value_type>(11))
		{
		}

	~FourLookupHashTable()
		{
		delete mTable;
		}

	bool contains(key_type key) const
		{
		lassert(key != 0);
		
		return mTable->contains(key);
		}

	const value_type& getValue(key_type key) const
		{
		lassert(key != 0);
		
		return mTable->getValue(key);
		}

	value_type& getValue(key_type key)
		{
		lassert(key != 0);
		
		return mTable->getValue(key);
		}

	//this function is NOT threadsafe because it has to create a temporary value of type value_type()
	//to which it returns a reference.
	value_type& operator[](key_type key)
		{
		lassert(key != 0);

		long slot = mTable->slotFor(key);

		if (slot != -1)
			return mTable->valueForSlot(slot);

		insert(key, value_type());
		return getValue(key);
		}

	static void staticInsertFunction(
					FourLookupHashTable* table,
					key_type key,
					value_type value
					)
		{
		table->insert(key, value);
		}

	bool insert(key_type key, value_type value)
		{
		lassert(key != 0);
		
		typename FourLookupHashTableMutexType<threadsafe>::lock_type lock(mMutex);

		if (contains(key))
			return false;

		lassert(!contains(key));

		if (mTable->insert(key, value))
			return true;

		long newSize = mTable->bucketCount() * 1.25;

		while (true)
			{
			newSize = nextSize(newSize);

			if (tryToReplaceTableWithSize(newSize, key, value))
				return true;
			}
		}

	size_t size() const
		{
		return mTable->size();
		}

	size_t bucketCount() const
		{
		return mTable->bucketCount();
		}

private:
	long nextSize(long inTableSize)
		{
		const static long sPrimesTable[] = {11,13,15,17,19,21,23,25,27,29,31,35,39,43,47,51,57,63,
			69,75,83,91,101,111,123,135,149,163,179,197,217,239,263,289,317,349,383,421,463,509,
			559,615,677,745,819,901,991,1091,1201,1321,1453,1599,1759,1935,2129,2341,2575,2833,
			3117,3429,3771,4149,4563,5019,5521,6073,6681,7349,8083,8891,9781,10759,11835,13019,
			14321,15753,17329,19061,20967,23063,25369,27905,30695,33765,37141,40855,44941,49435,
			54379,59817,65799,72379,79617,87579,96337,105971,116569,128225,141047,155151,170667,
			187733,206507,227157,249873,274861,302347,332581,365839,402423,442665,486931,535625,
			589187,648105,712915,784207,862627,948889,1043777,1148155,1262971,1389269,1528195,
			1681015,1849117,2034029,2237431,2461175,2707293,2978023,3275825,3603407,3963747,
			4360121,4796133,5275747,5803321,6383653,7022019,7724221,8496643,9346307,10280937,
			11309031,12439935,13683929,15052321,16557553,18213309,20034639,22038103,24241913,
			26666105,29332715,32265987,35492585,39041843,42946027,47240629,51964691,57161161,
			62877277,69165005,76081505,83689655,92058621,101264483,111390931,122530025,
			134783027,148261329,163087461,179396207,197335827,217069409,238776349,
			262653983,288919381,317811319,349592451,384551697,423006867,465307553,511838309,
			563022139,619324353,681256789,749382467,824320713,906752785,997428063,1097170869 
			};

		long ix = 0;
		while (sPrimesTable[ix] <= inTableSize)
			ix++;

		return sPrimesTable[ix];
		}

	bool tryToReplaceTableWithSize(long newSize, key_type key, value_type value)
		{
		UnresizableFourLookupHashTable<key_type, value_type>* newTable = 
			new UnresizableFourLookupHashTable<key_type, value_type>(newSize);

		if (!mTable->hashInto(*newTable) || !newTable->insert(key, value))
			{
			delete newTable;
			return false;
			}

		UnresizableFourLookupHashTable<key_type, value_type>* oldTable = mTable;
		mTable = newTable;
		
		if (threadsafe)
			//schedule this to be deleted on a background thread at some point in the future
			fourLookupHashTableDeletionCallbackScheduler()->schedule(
				boost::bind(deleteTable, oldTable),
				curClock() + .1
				);
		else
			delete oldTable;

		return true;
		}

	static void deleteTable(UnresizableFourLookupHashTable<key_type, value_type>* table)
		{
		delete table;
		}

	UnresizableFourLookupHashTable<key_type, value_type>* mTable;

	typename FourLookupHashTableMutexType<threadsafe>::mutex_type mMutex;
};

}
}

