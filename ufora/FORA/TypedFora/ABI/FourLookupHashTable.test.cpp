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
#include "FourLookupHashTable.hpp"

#include "../../../core/UnitTest.hpp"
#include "../../../core/Logging.hpp"
#include "../../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../../core/math/Random.hpp"
#include "../../../core/Clock.hpp"
#include "../../../core/threading/Queue.hpp"

using TypedFora::Abi::FourLookupHashTable;


BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FourLookupHashTable_basic )
	{
	FourLookupHashTable<long, long, false> hashTable;

	BOOST_CHECK(!hashTable.contains(10));
	hashTable.insert(10,10);
	BOOST_CHECK(hashTable.contains(10));
	
	hashTable[10] = 12;
	hashTable[12] = 13;

	BOOST_CHECK(hashTable.size() == 2);
	BOOST_CHECK(hashTable.bucketCount() > 1);

	BOOST_CHECK(hashTable.contains(10));
	BOOST_CHECK(!hashTable.contains(11));
	BOOST_CHECK(hashTable.contains(12));
	}

BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FourLookupHashTable_equivalent_to_map )
	{
	//deterministic test verifying that we are always equivalent to a map implementation
	FourLookupHashTable<long, long, false> hashTable;
	std::map<long, long> equivalentMap;

	for (long seed = 1; seed < 1000; seed++)
		{
		Ufora::math::Random::Uniform<float> generator(seed);

		long totalValues = generator() * 100;
		for (long k = 0; k < totalValues;k++)
			{
			long key = generator() * 50 + 1;
			long value = generator() * 5000;
			
			hashTable[key] = value;
			equivalentMap[key] = value;
			}

		lassert_dump(
			hashTable.size() == equivalentMap.size(), 
			hashTable.size() << " != " << equivalentMap.size() << " in seed " << seed 
				<< " with " << totalValues << " total values."
			);
		for (auto it = equivalentMap.begin(); it != equivalentMap.end(); ++it)
			lassert(hashTable.contains(it->first) && hashTable[it->first] == it->second);
		}
	}

BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FourLookupHashTable_overhead_grows_as_root_N )
	{
	FourLookupHashTable<long, long, false> hashTable;
	
	Ufora::math::Random::Uniform<float> generator(1);

	long k = 1;
	while (hashTable.bucketCount() < 1024 * 1024)
		{
		long priorCount = hashTable.bucketCount();

		hashTable[generator() * 1000000000 + 1] = 1;

		if (hashTable.bucketCount() != priorCount)
			{
			float bloat = hashTable.bucketCount() / (float)hashTable.size();
			float expectedBloat = std::sqrt(std::sqrt(hashTable.size()));

			BOOST_CHECK(bloat < expectedBloat * 2);

			LOG_INFO << "at table size " << hashTable.size() << ", bloat = " 
				<< bloat << " and expected bloat = " << expectedBloat;
			}
		}
	}

BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FourLookupHashTable_lookup_overhead )
	{
	FourLookupHashTable<long, long, false> hashTable;
	
	Ufora::math::Random::Uniform<float> generator(1);

	for (long k = 0; k < 1000;k++)
		hashTable[(k * k) % 10000 + 1] = 1;

	double t0 = curClock();
	for (long pass = 0; pass < 10000; pass++)
		for (long k = 0; k < 1000;k++)
			hashTable[(k * k) % 10000 + 1] = pass + 1;

	LOG_INFO << "FourLookupHashTable: 10 million writes in " << curClock() - t0;

	t0 = curClock();
	long ct = 0;
	for (long pass = 0; pass < 10000; pass++)
		for (long k = 0; k < 1000;k++)
			ct += hashTable[(k * k) % 10000 + 1];

	LOG_INFO << "FourLookupHashTable: 10 million reads in " << curClock() - t0;

	t0 = curClock();
	ct = 0;
	for (long pass = 0; pass < 10000; pass++)
		for (long k = 0; k < 1000;k++)
			ct += hashTable.getValue((k * k) % 10000 + 1);

	LOG_INFO << "FourLookupHashTable: 10 million getItems in " << curClock() - t0;
	
	t0 = curClock();
	ct = 0;
	for (long pass = 0; pass < 10000; pass++)
		for (long k = 0; k < 1000;k++)
			ct += hashTable.contains((k * k) % 10000 + 1);

	LOG_INFO << "FourLookupHashTable: 10 million containments in " << curClock() - t0;
	
	t0 = curClock();
	ct = 0;
	for (long pass = 0; pass < 10000; pass++)
		for (long k = 0; k < 1000;k++)
			ct += (k * k) % 10000 + 1;

	LOG_INFO << "FourLookupHashTable: 10 million index creations in " << curClock() - t0 << "(" << ct << ")";
	}

BOOST_AUTO_TEST_CASE( test_TypedFora_Abi_FourLookupHashTable_test_multithreading )
	{
	typedef FourLookupHashTable<long, long, true> hash_table_type;

	Queue<hash_table_type*> tableQueue;

	Queue<bool> hadErrorQueue;

	auto insertFunction = [&](long offset, long count) {
		while (true)
			{
			hash_table_type* table = tableQueue.get();

			//terminate if we read a null pointer
			if (!table)
				{
				//but write the null back so that all threads terminate
				tableQueue.write(table);
				return;
				}

			bool hadError = false;
			for (long k = 0; k < count; k++)
				{
				long key = (k + offset) % count + 1;

				if (table->contains(key))
					{
					long value = table->getValue(key);

					if (value != key)
						hadError = true;
					}
				else
					table->insert(key, key);
				}

			hadErrorQueue.write(hadError);
			}
		};

	std::vector<boost::thread> threads;

	for (long o = 0; o < 3; o++)
		for (long k = 0; k < 3; k++)
			threads.push_back(
				boost::thread(
					boost::bind(
						boost::function2<void, long, long>(insertFunction), 
						o, 
						20
						)
					)
				);

	double t0 = curClock();

	long count = 0;

	while (curClock() - t0 < 2.0)
		{
		count++;

		hash_table_type table;

		//trigger all the writer threads
		for (auto& t: threads)
			tableQueue.write(&table);

		//wait for them all to report success
		for (auto& t: threads)
			lassert(!hadErrorQueue.get());
		}

	//trigger thread termination
	tableQueue.write((hash_table_type*)0);

	for (auto& t: threads)
		t.join();
	}
