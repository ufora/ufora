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
#include "../VectorDataManager/VectorPage.hppml"
#include "../../core/Clock.hpp"
#include "../../core/UnitTest.hpp"

namespace {

const static int kSmallMemAmount = 8;
const static int kLargerMemAmount = 128;

}


BOOST_AUTO_TEST_CASE( test_MemoryPool_FreeStore )
	{
	MemoryPool* pool = MemoryPool::getFreeStorePool();

	//free store pool is a singleton
	BOOST_CHECK(
		pool == MemoryPool::getFreeStorePool()
		);


	uint8_t* data = pool->allocate(kSmallMemAmount);

	data = pool->realloc(data, kLargerMemAmount);
	pool->free(data);

	data = pool->realloc(0, kLargerMemAmount);
	data = pool->realloc(data, 0);

	BOOST_CHECK(data == 0);
	}

class TestMallocPool : public MemoryPool {
public:
	TestMallocPool() :
			MemoryPool(MemoryPool::MemoryPoolType::FreeStore)
		{
		}

	std::string stringRepresentation()
		{
		return "TestPool()";
		}

	Fora::ShareableMemoryBlockHandle convertPointerToShareableMemoryBlock(uint8_t* inBytes, int64_t bytes)
		{
		lassert(false);
		}

	uint8_t* importShareableMemoryBlock(const Fora::ShareableMemoryBlockHandle& inHandle)
		{
		lassert(false);
		}

	virtual uint8_t* allocate(size_t inBytes)
		{
		return (uint8_t*)malloc(inBytes);
		}

	virtual void free(uint8_t* inBytes)
		{
		::free(inBytes);
		}

	virtual uint8_t* realloc(uint8_t* inBytes, uword_t inNewBytes)
		{
		return (uint8_t*) ::realloc(inBytes, inNewBytes);
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

	void vectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage,
						boost::shared_ptr<Ufora::threading::Trigger> mappedPageWantsUnmapped
						)
		{
		lassert_dump(false, "this should never happen. Mapping vectors in the free-store can't work");
		}

	bool isVectorPageMapped(
						boost::shared_ptr<VectorPage> mappedPage
						)
		{
		return false;
		}
};

BOOST_AUTO_TEST_CASE( test_MemoryPool_FreeStore_performance )
	{
	double t0 = curClock();

	long bestMalloc = 0, bestFreeStore = 0;

	for (long trial = 0; trial < 20; trial++)
		{
		uint8_t* pointers[1000];

		MemoryPool* pool = new TestMallocPool();

		long countMallocAndFree = 0;

		while (curClock() - t0 < .10)
			{
			for (long k = 0; k < 1000; k++)
				pointers[k] = pool->allocate(k+1);

			for (long k = 0; k < 1000; k++)
				pool->free(pointers[k]);

			countMallocAndFree++;
			}

		delete pool;
		pool = MemoryPool::getFreeStorePool();

		t0 = curClock();

		long countFreeStorePool = 0;

		while (curClock() - t0 < .10)
			{
			for (long k = 0; k < 1000; k++)
				pointers[k] = pool->allocate(k+1);

			for (long k = 0; k < 1000; k++)
				pool->free(pointers[k]);

			countFreeStorePool++;
			}

		bestMalloc = std::max<long>(bestMalloc, countMallocAndFree);
		bestFreeStore = std::max<long>(bestFreeStore, countFreeStorePool);
		}

	//currently, the free store pool is much slower than regular allocation
	LOG_INFO << "ratio is " << (double)bestFreeStore / (double)bestMalloc << "\n"
		<< "free store: " << bestFreeStore << "\n"
		<< "malloc    : " << bestMalloc << "\n"
		;

	BOOST_CHECK(bestMalloc < bestFreeStore * 2);
	}


