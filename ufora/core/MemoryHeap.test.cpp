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
#include "MemoryHeap.hpp"
#include "MemoryUtil.hpp"
#include <map>
#include <sys/mman.h>
#include <vector>
#include "math/Random.hpp"
#include "UnitTest.hpp"
#include <vector>

using namespace std;

const int SMALL_HEAP_SIZE = 64 * 1024;
const int MEDIUM_HEAP_SIZE = 1 * 1024 * 1024;
const int LARGE_HEAP_SIZE = 64 * 1024 * 1024;

namespace {

void *mremapPassthrough(void *old_address, size_t old_size,
                    size_t new_size, int flags)
	{
	return ::mremap(old_address, old_size, new_size, flags);
	}

boost::shared_ptr<MemoryHeap> newStandardHeap()
	{
	return boost::shared_ptr<MemoryHeap>(
		new MemoryHeap(
			boost::bind(
				&::mmap,
				(void*)0,
				boost::arg<1>(),
				PROT_READ | PROT_WRITE,
				MAP_ANONYMOUS | MAP_PRIVATE,
				-1,
				0
				),
			::munmap,
			::mremap
			)
		);
	}

}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_init )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	void* ptr = heap->malloc(8);
	BOOST_CHECK(ptr != NULL);

	BOOST_CHECK_LE(heap->getHeapSize(), MemoryHeap::DEFAULT_PAGE_SIZE * 2); // dlmalloc doesn't always shrink below two allocated segments

	heap->validate();
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_fillAndEmpty )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	std::vector<void*> allocs;

	for (int i=0; i<3; ++i)
		{
		while (true)
			{
			void* ptr = heap->malloc(8);
			heap->validate();

			allocs.push_back(ptr);

			if (heap->getHeapSize() > MEDIUM_HEAP_SIZE)
				break;

			ptr = heap->malloc(MemoryHeap::DEFAULT_PAGE_SIZE + 8);
			heap->validate();

			allocs.push_back(ptr);

			if (heap->getHeapSize() > MEDIUM_HEAP_SIZE)
				break;
			}

		while (allocs.size() > 0)
			{
			heap->free(*(allocs.end() - 1));
			heap->validate();
			allocs.pop_back();
			}

		BOOST_CHECK_LE(heap->getBytesUsed(), 0);

		heap->trim(0);
		heap->validate();
		BOOST_CHECK_LE(heap->getHeapSize(), MemoryHeap::DEFAULT_PAGE_SIZE * 2); // dlmalloc doesn't always shrink below two allocated segments
		}

	heap->validate();
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_basicAllocation )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	size_t oldHeapSize = heap->getHeapSize();
	size_t oldBytesUsed = heap->getBytesUsed();

	for (int sz=0; sz < MemoryHeap::DEFAULT_PAGE_SIZE * 4; sz = sz * 1.5 + 7)
		{
		void* ptr = heap->malloc(sz);
		BOOST_CHECK(ptr != NULL);

		size_t newHeapSize = heap->getHeapSize();
		BOOST_CHECK_GE(newHeapSize, oldHeapSize);

		size_t newBytesUsed = heap->getBytesUsed();
		BOOST_CHECK_GT(newBytesUsed, oldBytesUsed);

		oldHeapSize = newHeapSize;
		oldBytesUsed = newBytesUsed;
		}

	heap->validate();
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_basicFree )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	size_t oldHeapSize = heap->getHeapSize();
	size_t oldBytesUsed = heap->getBytesUsed();

	for (int sz=0; sz < MemoryHeap::DEFAULT_PAGE_SIZE * 4; sz++)
		{
		void* ptr = heap->malloc(sz);
		BOOST_CHECK(ptr != NULL);

		size_t newHeapSize = heap->getHeapSize();
		BOOST_CHECK_GE(newHeapSize, oldHeapSize);

		size_t newBytesUsed = heap->getBytesUsed();
		BOOST_CHECK_GT(newBytesUsed, oldBytesUsed);

		oldHeapSize = newHeapSize;
		oldBytesUsed = newBytesUsed;

		heap->free(ptr);

		newHeapSize = heap->getHeapSize();
		BOOST_CHECK_LE(newHeapSize, oldHeapSize);

		newBytesUsed = heap->getBytesUsed();
		BOOST_CHECK_LT(newBytesUsed, oldBytesUsed);

		oldHeapSize = newHeapSize;
		oldBytesUsed = newBytesUsed;
		}

	BOOST_CHECK_LE(heap->getBytesUsed(), 0);

	heap->validate();
	}


BOOST_AUTO_TEST_CASE( test_MemoryHeap_allocLargerThanPage )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	size_t oldHeapSize = heap->getHeapSize();
	size_t oldBytesUsed = heap->getBytesUsed();

	for (int i=0; i<10; ++i)
		{
		void* ptr = heap->malloc(SMALL_HEAP_SIZE * (i + 2));
		BOOST_CHECK(ptr != NULL);

		size_t newHeapSize = heap->getHeapSize();
		BOOST_CHECK_GT(newHeapSize, oldHeapSize);

		size_t newBytesUsed = heap->getBytesUsed();
		BOOST_CHECK_GT(newBytesUsed, oldBytesUsed);

		oldHeapSize = newHeapSize;
		oldBytesUsed = newBytesUsed;
		}
	heap->validate();
	}

int rand_in_range(int low, int high)
	{
	return rand() % (high - low + 1) + low;
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_massiveAllocs )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	size_t oldSize = heap->getHeapSize();

	std::vector<void*> allocs;

	for (int i=0; i<10; ++i)
		{
		void* ptr = heap->malloc(rand_in_range(64, MEDIUM_HEAP_SIZE*2));
		BOOST_CHECK(ptr != NULL);

		allocs.push_back(ptr);

		size_t newSize = heap->getHeapSize();
		BOOST_CHECK_GE(newSize, oldSize);
		oldSize = newSize;
		}

	for (int i=0; i<10; ++i)
		{
		heap->free(allocs[i]);
		size_t newSize = heap->getHeapSize();
		BOOST_CHECK_LE(newSize, oldSize);
		oldSize = newSize;
		}

	size_t preTrim = heap->getHeapSize();
	heap->trim(0);
	size_t postTrim = heap->getHeapSize();
	BOOST_CHECK_GE(preTrim, postTrim);
	heap->validate();
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_largeAllocSize )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	void* p1 = heap->malloc(heap->getLargeAllocSize() / 2);

	BOOST_CHECK(!heap->isLargeAlloc(p1));

	heap->free(p1);

	p1 = heap->malloc(heap->getLargeAllocSize());

	BOOST_CHECK(heap->isLargeAlloc(p1));

	heap->free(p1);
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_largeAlloc_and_resizing )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	void* p1 = heap->malloc(16);
	p1 = heap->realloc(p1, heap->getLargeAllocSize() * 2);

	BOOST_CHECK(heap->isLargeAlloc(p1));

	p1 = heap->realloc(p1, 16);

	BOOST_CHECK(!heap->isLargeAlloc(p1));

	heap->free(p1);
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_random_behavior )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	map<char*, size_t> currentSizes;
	map<char*, char> currentValue;
	std::vector<char*> allValues;

	size_t totalAllocated = 0;

	Ufora::math::Random::Uniform<float> rnd(1);

	long maxSize = MemoryHeap::DEFAULT_PAGE_SIZE * 2;

	for (long k = 0; k < 10000;k++)
		{
		if (rnd() < .25 && totalAllocated < 100 * 1024 * 1024)
			{
			//allocate a new one
			int size = 16 + (maxSize - 16) * rnd();

			char* data = (char*)heap->malloc(size);

			char val = rnd() * 128;

			memset(data, val, size);

			currentSizes[data] = size;
			currentValue[data] = val;
			totalAllocated += size;
			allValues.push_back(data);
			}
			else
		if (rnd() < .5 && totalAllocated < 100 * 1024 * 1024 && currentSizes.size())
			{
			int valIx = rnd() * allValues.size();

			char* aValue = allValues[valIx];
			allValues.erase(allValues.begin() + valIx);

			int oldSize = currentSizes[aValue];
			char curVal = currentValue[aValue];

			currentSizes.erase(aValue);
			currentValue.erase(aValue);

			int newSize;

			if (rnd() < .01)
				newSize = oldSize;
			else
				newSize = 16 + (maxSize - 16) * rnd();

			//verify the values
			for (long k = 0; k < oldSize; k++)
				{
				lassert(curVal == aValue[k]);
				}

			//resize
			char* newValue = (char*)heap->realloc((char*)aValue, newSize);

			//verify the values
			for (long k = 0; k < std::min<size_t>(oldSize, newSize); k++)
				{
				lassert(curVal == newValue[k]);
				}

			for (long k = std::min<size_t>(oldSize, newSize); k < newSize; k++)
				newValue[k] = curVal;

			currentSizes[newValue] = newSize;
			currentValue[newValue] = curVal;
			totalAllocated += newSize - oldSize;

			allValues.push_back(newValue);
			}
			else
		if (currentSizes.size())
			{
			int valIx = rnd() * allValues.size();

			char* aValue = allValues[valIx];
			allValues.erase(allValues.begin() + valIx);

			int oldSize = currentSizes[aValue];
			char curVal = currentValue[aValue];

			currentSizes.erase(aValue);
			currentValue.erase(aValue);

			//verify the values
			for (long k = 0; k < oldSize; k++)
				{
				lassert(curVal == aValue[k]);
				}

			//resize
			heap->free(aValue);
			totalAllocated -= oldSize;
			}
		}
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_detach )
	{
	boost::shared_ptr<MemoryHeap> heap = newStandardHeap();

	void* p1 = heap->malloc(heap->getLargeAllocSize());
	size_t sz = heap->msize(p1);

	BOOST_CHECK(sz == heap->getLargeAllocSize());

	BOOST_CHECK(heap->isLargeAlloc(p1));

	heap->detachLargeAlloc(p1);

	heap.reset();

	BOOST_CHECK(munmap(p1, sz) == 0);
	}

/*
//TODO: rewrite this using boost::thread instead of pthreads

namespace {

struct thread_args {
	std::vector<boost::shared_ptr<MemoryHeap> > heaps;
	int idx;
};

}

void* thread(void* _args)
	{
	thread_args* args = (thread_args*)_args;
	MemoryHeap* heap = args->heaps[args->idx];
	std::vector<void*> allocs;

	void* initial_alloc = heap->malloc(rand_in_range(1, 64));
	lassert(initial_alloc != NULL);

	for(int i=0; i<10; ++i)
		{
		for (int j=0; j<i*100; ++j)
			{
			void* malloc1 = heap->malloc(rand_in_range(1, 64));
			lassert(malloc1 != NULL);
			void* realloc1 = heap->malloc(rand_in_range(1, 64));
			lassert(realloc1 != NULL);
			void* calloc1 = heap->calloc(rand_in_range(1, 64), 5);
			lassert(calloc1 != NULL);
			void* malloc2 = heap->malloc(rand_in_range(1, 64));
			lassert(malloc2 != NULL);
			void* realloc2 = heap->malloc(rand_in_range(1, 64));
			lassert(realloc2 != NULL);
			void* calloc2 = heap->calloc(rand_in_range(1, 64), 5);
			lassert(calloc2 != NULL);

			realloc1 = heap->realloc(realloc1, rand_in_range(1, 64) * 10);
			lassert(realloc1 != NULL);
			realloc2 = heap->realloc(realloc2, rand_in_range(1, 64) * 10);
			lassert(realloc2 != NULL);

			heap->free(malloc1);
			heap->free(realloc1);
			heap->free(calloc1);

			allocs.push_back(malloc2);
			allocs.push_back(realloc2);
			allocs.push_back(calloc2);
			}

		void* large_malloc1 = heap->malloc(rand_in_range(64, MEDIUM_HEAP_SIZE*2));
		lassert(large_malloc1 != NULL);
		void* large_malloc2 = heap->malloc(rand_in_range(64, MEDIUM_HEAP_SIZE*2));
		lassert(large_malloc2 != NULL);

		heap->free(large_malloc1);
		allocs.push_back(large_malloc2);

		heap->validate();
		}

	for(int i=0; i<allocs.size(); ++i)
		heap->free(allocs[i]);

	heap->free(initial_alloc);

	BOOST_CHECK_EQUAL(heap->getBytesUsed(), 0);

	heap->validate();

	size_t preTrim = heap->getHeapSize();
	heap->trim(0);
	size_t postTrim = heap->getHeapSize();
	lassert(preTrim >= postTrim);

	heap->validate();

	delete args;
	return NULL;
	}

BOOST_AUTO_TEST_CASE( test_MemoryHeap_multithreaded )
	{
	std::vector<boost::shared_ptr<MemoryHeap> > heaps;

	for (int i=0; i<8; ++i)
		heaps.push_back(newStandardHeap());

	for (int i=0; i<8; ++i)
		heaps.push_back(newStandardHeap());

	for (int i=0; i<8; ++i)
		heaps.push_back(newStandardHeap());

	std::vector<pthread_t> threads(heaps.size());
	for (int i=0; i<threads.size(); ++i)
		{
		thread_args* args = new thread_args();
		args->heaps = heaps;
		args->idx = i;
		int result = pthread_create(&threads[i], NULL, &thread, args);
		BOOST_CHECK_EQUAL(result, 0);
		}

	for (int i=0; i<threads.size(); ++i)
		{
		pthread_join(threads[i], NULL);
		}
	}
*/

