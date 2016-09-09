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
#include "MutableVectorHandle.hpp"
#include "../../../core/Logging.hpp"
#include "../../Core/MemoryPool.hpp"
#include "../../VectorDataManager/VectorDataMemoryManager.hppml"
#include "../../Core/ImplValContainerUtilities.hppml"
#include "../../Core/ExecutionContext.hppml"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/UnitTestCppml.hpp"
#include "../../../core/math/Random.hpp"

using TypedFora::Abi::MutableVectorHandle;

class TestMutableVectorHandleFixture {
public:
	TestMutableVectorHandleFixture() :
			memoryPool(
				0,
				PolymorphicSharedPtr<VectorDataMemoryManager>(
					new VectorDataMemoryManager(
						CallbackScheduler::singletonForTesting(),
						CallbackScheduler::singletonForTesting()
						)
					)
				)
		{
		}

	ExecutionContextMemoryPool memoryPool;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_MutableVectorHandle, TestMutableVectorHandleFixture )

BOOST_AUTO_TEST_CASE ( test_refcounts )
	{
	MutableVectorHandle* handle = new MutableVectorHandle(&memoryPool, JOV(), hash_type());

	handle->incrementRefcount();

	BOOST_CHECK(!handle->decrementRefcount());
	BOOST_CHECK(handle->decrementRefcount());
	}

BOOST_AUTO_TEST_CASE ( test_instantiate )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	BOOST_CHECK_EQUAL(handle.size(), 0);
	BOOST_CHECK_EQUAL_CPPML(handle.elementJOV(), JOV());
	}

BOOST_AUTO_TEST_CASE ( test_allocate )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	handle.resize(10, ImplValContainer());
	}

BOOST_AUTO_TEST_CASE ( test_resize )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	handle.resize(10, ImplValContainer());
	handle.resize(5, ImplValContainer());
	handle.resize(0, ImplValContainer());
	}

BOOST_AUTO_TEST_CASE ( test_typed )
	{
	MutableVectorHandle handle(&memoryPool, JOV::OfType(Type::String()), hash_type());

	ImplValContainer aString =
		ImplValContainerUtilities::createString(String("this is a long string", &memoryPool));

	ImplValContainer aDifferentString =
		ImplValContainerUtilities::createString(String("this is another long string", &memoryPool));

	ImplValContainer aThirdString =
		ImplValContainerUtilities::createString(String("this is a different one", &memoryPool));

	handle.resize(10, aString);

	BOOST_CHECK(handle.size() == 10);
	BOOST_CHECK(handle[4] == aString);

	handle.resize(5, aString);

	BOOST_CHECK(handle.size() == 5);
	BOOST_CHECK(handle[4] == aString);

	handle.resize(10, aDifferentString);

	BOOST_CHECK(handle.size() == 10);
	BOOST_CHECK(handle[4] == aString);
	BOOST_CHECK(handle[8] == aDifferentString);

	handle.setItem(4, aThirdString);
	BOOST_CHECK(handle[4] == aThirdString);
	}

BOOST_AUTO_TEST_CASE ( test_untyped )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	ImplValContainer aString =
		ImplValContainerUtilities::createString(String("this is a long string", &memoryPool));

	ImplValContainer aDifferentString =
		ImplValContainerUtilities::createString(String("this is another long string", &memoryPool));

	ImplValContainer anInteger(CSTValue(10));

	handle.resize(10, aString);

	BOOST_CHECK(handle.size() == 10);
	BOOST_CHECK(handle[4] == aString);

	handle.shrink(5);

	handle.setItem(3, anInteger);
	BOOST_CHECK(handle[2] == aString);
	BOOST_CHECK(handle[3] == anInteger);
	BOOST_CHECK(handle[4] == aString);

	handle.resize(10, anInteger);
	BOOST_CHECK(handle[4] == aString);
	BOOST_CHECK(handle[3] == anInteger);
	BOOST_CHECK(handle[8] == anInteger);
	}


BOOST_AUTO_TEST_SUITE_END( )

