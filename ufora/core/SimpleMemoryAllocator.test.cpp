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
#include "SimpleMemoryAllocator.hpp"
#include "UnitTest.hpp"
#include <vector>

BOOST_AUTO_TEST_CASE( test_SimpleMemoryAllocator_emptyAllocatorIsConsistent )
	{
	SimpleMemoryAllocator allocator(1024, 8);

	allocator.checkInternalConsistency();
	}

BOOST_AUTO_TEST_CASE( test_SimpleMemoryAllocator_allocationWorks )
	{
	SimpleMemoryAllocator allocator(1024, 8);

	BOOST_CHECK_EQUAL(allocator.allocate(10), 0);

	allocator.checkInternalConsistency();

	allocator.freeAtOffset(0);

	allocator.checkInternalConsistency();
	}

BOOST_AUTO_TEST_CASE( test_SimpleMemoryAllocator_allocationWorks_2 )
	{
	SimpleMemoryAllocator allocator(96, 8);

	allocator.allocate(32);
	allocator.allocate(32);
	allocator.allocate(32);

	allocator.checkInternalConsistency();

	allocator.freeAtOffset(32);

	allocator.checkInternalConsistency();

	allocator.allocate(16);

	allocator.checkInternalConsistency();

	allocator.allocate(16);

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 0);
	}

BOOST_AUTO_TEST_CASE( test_SimpleMemoryAllocator_allocationAndFreeingWork )
	{
	SimpleMemoryAllocator allocator(1024, 8);

	for (long k = 0; k < 1024; k += 8)
		allocator.allocate(8);

	allocator.checkInternalConsistency();

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 0);

	//free every other block
	for (long k = 0; k < 1024; k += 16)
		allocator.freeAtOffset(k);

	allocator.checkInternalConsistency();

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 8);

	//reallocate them
	for (long k = 0; k < 1024; k += 16)
		allocator.allocate(8);

	allocator.checkInternalConsistency();

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 0);

	//free in chunks
	for (long k = 0; k < 1024; k += 32)
		{
		allocator.freeAtOffset(k);
		allocator.freeAtOffset(k + 8);
		}

	allocator.checkInternalConsistency();

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 16);

	//free everything
	for (long k = 0; k < 1024; k += 32)
		{
		allocator.freeAtOffset(k + 16);
		allocator.freeAtOffset(k + 24);
		}

	allocator.checkInternalConsistency();

	BOOST_CHECK_EQUAL(allocator.maxAllocatableBlockSize(), 1024);
	}

BOOST_AUTO_TEST_CASE( test_SimpleMemoryAllocator_randomAllocationAndFreeing )
	{
	SimpleMemoryAllocator allocator(1024* 1024, 8);

	std::vector<uword_t> allocatedBlocks;
	srand(0);

	for (long k = 0; k < 10000;k++)
		{
		allocatedBlocks.push_back(allocator.allocate(rand() * 1000 / (float)RAND_MAX));

		allocator.checkInternalConsistency();

		if (allocatedBlocks.size() > 150)
			{
			uword_t index = rand() * allocatedBlocks.size() / RAND_MAX;

			allocator.freeAtOffset(allocatedBlocks[index]);
			allocatedBlocks.erase(allocatedBlocks.begin() + index);
			allocator.checkInternalConsistency();
			}
		}

	while (allocatedBlocks.size())
		{
		allocator.freeAtOffset(allocatedBlocks.back());
		allocatedBlocks.pop_back();
		allocator.checkInternalConsistency();
		}
	}

