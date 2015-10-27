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
#include "MutableVectorRecord.hppml"
#include "../VectorDataManager/VectorDataMemoryManager.hppml"
#include "../../core/UnitTest.hpp"
#include "../Core/Type.hppml"
#include "../Core/MemoryPool.hpp"
#include "../Core/ExecutionContextMemoryPool.hppml"
#include "../TypedFora/ABI/MutableVectorHandle.hpp"


namespace {
PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());
}

BOOST_AUTO_TEST_SUITE( test_FORA_MutableVector )

BOOST_AUTO_TEST_CASE( test_FORA_MutableVector_create_destroy )
{
	boost::shared_ptr<ExecutionContextMemoryPool> pool(
		new ExecutionContextMemoryPool(0, 
			PolymorphicSharedPtr<VectorDataMemoryManager>(
				new VectorDataMemoryManager(scheduler, scheduler)
				)
			)
		);

	MutableVectorRecord record = 
		MutableVectorRecord::allocateNewMutableVectorRecordOfNothing(
			pool.get()
			);
}

	
BOOST_AUTO_TEST_CASE( test_FORA_MutableVector_Type_Interface )
{
	boost::shared_ptr<ExecutionContextMemoryPool> pool(
		new ExecutionContextMemoryPool(0, 
			PolymorphicSharedPtr<VectorDataMemoryManager>(
				new VectorDataMemoryManager(scheduler, scheduler)
				)
			)
		);

	Type vecType = Type::MutableVector();

	BOOST_CHECK_EQUAL(vecType.size(), sizeof(MutableVectorRecord));

	BOOST_CHECK(!vecType.isPOD());

	char recordStorage[sizeof(MutableVectorRecord)];

	char recordStorage2[sizeof(MutableVectorRecord)];

	vecType.initialize(recordStorage, pool.get());

	BOOST_CHECK_EQUAL(
		(**(TypedFora::Abi::MutableVectorHandle**)recordStorage).refcount(), 
		1
		);

	vecType.initialize(&recordStorage2, &recordStorage);

	BOOST_CHECK_EQUAL(
		(**(TypedFora::Abi::MutableVectorHandle**)recordStorage).refcount(), 
		2
		);	

	vecType.destroy(recordStorage);

	BOOST_CHECK_EQUAL(
		(**(TypedFora::Abi::MutableVectorHandle**)recordStorage).refcount(), 
		1
		);

	vecType.destroy(recordStorage);
}

BOOST_AUTO_TEST_SUITE_END()

