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
#include "ForaValueArray.hppml"
#include "ForaValueArrayImpl.hppml"
#include "ForaValueArrayTestFixture.hppml"
#include "ForaValueArraySpaceRequirements.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/math/Random.hpp"
#include "../../../core/threading/CallbackScheduler.hppml"

using TypedFora::Abi::ForaValueArray;
using TypedFora::Abi::ForaValueArrayImpl;
using TypedFora::Abi::PackedForaValues;


BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_ForaValueArray, ForaValueArrayTestFixture )

BOOST_AUTO_TEST_CASE ( test_instantiate_execution_context )
	{
	ForaValueArrayImpl array(&memoryPool);

	BOOST_CHECK(array.isWriteable());
	}

BOOST_AUTO_TEST_CASE ( test_append_POD )
	{
	ForaValueArrayImpl array(&memoryPool);

	BOOST_CHECK_EQUAL(array.size(), 0);
	BOOST_CHECK(!array.isHomogenous());

	array.append(ImplValContainer(CSTValue((uint64_t)10)));

	BOOST_CHECK_EQUAL(array.size(), 1);
	BOOST_CHECK(array.isHomogenous());
	BOOST_CHECK(array.getHomogenousJOV() == JudgmentOnValue::OfType(Type::Integer(64, false)));

	array.append(ImplValContainer(CSTValue((uint64_t)11)));

	BOOST_CHECK_EQUAL(array.size(), 2);
	BOOST_CHECK(array.isHomogenous());
	}

BOOST_AUTO_TEST_CASE ( test_entuple_POD )
	{
	ForaValueArrayImpl array(&memoryPool);

	for (int64_t k = 0; k < 100; k++)
		array.append(ImplValContainer(CSTValue((uint64_t)k)));

	array.entuple(Type::Integer(32,true));

	BOOST_CHECK_EQUAL(array.size(), 100);
	BOOST_CHECK(array.isHomogenous());
	BOOST_CHECK_EQUAL(array.getHomogenousJOV().type()->size(), 12);

	BOOST_CHECK_EQUAL(((uint64_t*)array.offsetFor(0))[0], 0);
	BOOST_CHECK_EQUAL(((uint64_t*)array.offsetFor(90))[0], 90);

	array.detuple(Type::Integer(32,true));

	BOOST_CHECK(array.getHomogenousJOV().type()->size() == 8);

	BOOST_CHECK_EQUAL(((uint64_t*)array.offsetFor(0))[0], 0);
	BOOST_CHECK_EQUAL(((uint64_t*)array.offsetFor(90))[0], 90);
	}

BOOST_AUTO_TEST_CASE ( test_append_and_pack )
	{
	ForaValueArrayImpl array1(&memoryPool);
	ForaValueArrayImpl array2(&memoryPool);

	for (long k = 0; k < 100; k++)
		array1.append(
			k % 2 ? ImplValContainer() : ImplValContainer(CSTValue((uint64_t)k))
			);

	array2.prepareForAppending(array1.getSpaceRequirements());
	array2.append(array1);

	BOOST_CHECK(array2.usingJudgmentTable());
	BOOST_CHECK_EQUAL(array2.judgmentCount(), 2);
	BOOST_CHECK(!array2.usingOffsetTable());
	BOOST_CHECK_EQUAL(array2.homogenousStride(), sizeof(uint64_t));
	}

BOOST_AUTO_TEST_CASE ( test_append_POD_heterogeneous )
	{
	ForaValueArrayImpl array(&memoryPool);

	BOOST_CHECK_EQUAL(array.size(), 0);
	BOOST_CHECK(!array.isHomogenous());

	array.append(ImplValContainer(CSTValue((uint64_t)10)));
	array.append(ImplValContainer(CSTValue((double)10.0)));

	BOOST_CHECK_EQUAL(array.size(), 2);
	BOOST_CHECK(!array.isHomogenous());
	}

BOOST_AUTO_TEST_CASE ( test_append_non_POD )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));

	BOOST_CHECK_EQUAL(array.size(), 1);

	BOOST_CHECK(array.isHomogenous());
	}

BOOST_AUTO_TEST_CASE ( test_append_POD_repeatedly )
	{
	ForaValueArrayImpl array(&memoryPool);

	ImplValContainer i(CSTValue(10));

	for (long k = 0; k < 10000; k++)
		array.append(i);

	BOOST_CHECK_EQUAL(array.size(), 10000);

	BOOST_CHECK(array.isHomogenous());
	}

BOOST_AUTO_TEST_CASE ( test_append_constant_judgment )
	{
	ForaValueArrayImpl array(&memoryPool);

	CSTValue c(123);

	JudgmentOnValue constantJOV = jovEmptyVector();

	array.append(ImplValContainer(CSTValue(0)));

	array.append(constantJOV, (uint8_t*)constantJOV.constant()->getReference().data(), 1, 0);

	BOOST_CHECK(array[1] == ImplValContainer(*constantJOV.constant()));
	}

BOOST_AUTO_TEST_CASE ( test_append_non_POD_2 )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));

	BOOST_CHECK_EQUAL(array.size(), 3);

	BOOST_CHECK(array.isHomogenous());
	}

BOOST_AUTO_TEST_CASE ( test_append_non_POD_mixed )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainerUtilities::createBool(false));
	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	array.append(ImplValContainerUtilities::createBool(false));
	}

BOOST_AUTO_TEST_CASE ( test_append_vector_of_vector )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(vectorOfFloat);
	array.append(vectorOfEmptyVector);

	BOOST_CHECK(array[0] == vectorOfFloat);
	BOOST_CHECK(array[1] == vectorOfEmptyVector);
	}

BOOST_AUTO_TEST_CASE ( test_append_vector_of_vector_2 )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(vectorOfEmptyVector);
	array.append(vectorOfFloat);

	BOOST_CHECK(array[0] == vectorOfEmptyVector);
	BOOST_CHECK(array[1] == vectorOfFloat);
	}

BOOST_AUTO_TEST_CASE ( test_append_vector_of_vector_3 )
	{
		{
		ForaValueArrayImpl array(&memoryPool);

		array.append(emptyVector);
		array.append(vectorOfEmptyVector);
		array.append(vectorOfFloat);

		//BOOST_CHECK(array[0] == emptyVector);
		//BOOST_CHECK(array[1] == vectorOfEmptyVector);
		//BOOST_CHECK(array[2] == vectorOfFloat);
		}

		{
		ForaValueArrayImpl array(&memoryPool);

		array.append(emptyVector);
		array.append(vectorOfEmptyVector);
		array.append(vectorOfFloat);

		BOOST_CHECK(array[0] == emptyVector);
		BOOST_CHECK(array[1] == vectorOfEmptyVector);
		BOOST_CHECK(array[2] == vectorOfFloat);
		}
	}

BOOST_AUTO_TEST_CASE ( test_append_non_POD_mixed_2 )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	array.append(ImplValContainerUtilities::createBool(false));
	}

BOOST_AUTO_TEST_CASE ( test_append_non_POD_mixed_and_entuple )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	array.append(ImplValContainerUtilities::createBool(false));
	array.append(ImplValContainerUtilities::createString(String("this is a big string", &memoryPool)));
	
	array.entuple(Type::Integer(32,false));

	BOOST_CHECK_EQUAL( ((String*)array.offsetFor(2))->stdString(), "this is a big string" );

	array.detuple(Type::Integer(32,false));

	BOOST_CHECK_EQUAL( ((String*)array.offsetFor(2))->stdString(), "this is a big string" );
	}

BOOST_AUTO_TEST_CASE ( test_blit_strings_speed )
	{
	std::vector<uint8_t> someData1, someData2;

	const static long count = 1000000;

	someData1.resize(sizeof(String) * count);
	someData2.resize(sizeof(String) * count);

	Type s = Type::String();

	double t0 = curClock();
	s.initialize(&someData1[0], count, sizeof(String), &memoryPool);
	LOG_INFO << "took " << curClock() - t0 << " to initialize 1mm";

	double t1 = curClock();
	s.initialize(&someData2[0], &someData1[0], count, sizeof(String), sizeof(String));
	LOG_INFO << "took " << curClock() - t1 << " to copy 1mm old-style";

	double t2 = curClock();
	s.destroy(&someData2[0], count, sizeof(String));
	LOG_INFO << "took " << curClock() - t2 << " to destroy 1mm old-style";

	std::vector<void*> targets1;
	std::vector<void*> targets2;
	targets1.resize(count);
	targets2.resize(count);

	for (long k = 0; k < count; k++)
		targets1[k] = &someData1[0] + sizeof(String) * k;

	for (long k = 0; k < count; k++)
		targets2[k] = &someData2[0] + sizeof(String) * k;

	double t3 = curClock();
	s.initializeScattered((void**)&targets1[0], count, 0, &memoryPool);
	LOG_INFO << "Took " << curClock() - t3 << " to initialize 1mm scattered";

	double t4 = curClock();
	s.initializeScattered((void**)&targets2[0], (const void**)&targets1[0], count, 0, 0);
	LOG_INFO << "Took " << curClock() - t4 << " to copy 1mm scattered";

	double t5 = curClock();
	s.destroyScattered((void**)&targets2[0], count, 0);
	LOG_INFO << "Took " << curClock() - t5 << " to destroy 1mm scattered";

	s.destroyScattered((void**)&targets1[0], count, 0);
	}

BOOST_AUTO_TEST_CASE ( test_deserialization_preparation )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainer());
	array.append(ImplValContainerUtilities::createDouble(0.0));
	array.append(ImplValContainer());
	array.append(ImplValContainerUtilities::createDouble(0.0));

	ForaValueArrayImpl array2(&memoryPool);
	array2.prepareForAppending(array.getSpaceRequirements());

	array2.append(array);

	BOOST_REQUIRE(array.size() == array2.size());

	for (long k = 0; k < array.size(); k++)
		BOOST_CHECK(array[k] == array2[k]);
	}

BOOST_AUTO_TEST_CASE ( test_deserialization_preparation_for_slice )
	{
	ForaValueArrayImpl array(&memoryPool);

	array.append(ImplValContainer());
	array.append(ImplValContainerUtilities::createDouble(0.0));
	array.append(ImplValContainer());
	array.append(ImplValContainerUtilities::createDouble(0.0));

	ForaValueArrayImpl array2(&memoryPool);
	array2.prepareForAppending(array.getSpaceRequirements(0, 1));

	array2.append(array, 0, 1);

	BOOST_CHECK(array[0] == array2[0]);
	}

BOOST_AUTO_TEST_CASE ( test_append_pod )
	{
	for (long shouldCompress = 0; shouldCompress < 2; shouldCompress++)
		for (long passes = 0; passes < 10; passes++)
			{
			ForaValueArrayImpl array(&memoryPool);
			ForaValueArrayImpl array2(&memoryPool);
			ForaValueArrayImpl array3(&memoryPool);

			ImplValContainer intIvc = ImplValContainer(CSTValue((int64_t)10));
			ImplValContainer nothingIvc = ImplValContainer();

			array2.append(intIvc);
			array2.append(intIvc);
			array2.append(intIvc);

			array3.append(intIvc);
			array3.append(nothingIvc);
			array3.append(nothingIvc);
			array3.append(intIvc);
			array3.append(intIvc);

			if (shouldCompress)
				{
				TypedFora::Abi::ForaValueArraySpaceRequirements reqs;

				for (long k = 0; k < 10 + passes; k++)
					reqs = reqs + array2.getSpaceRequirements() + array3.getSpaceRequirements();

				array.prepareForAppending(reqs);
				}

			for (long k = 0; k < 10 + passes; k++)
				{
				array.append(array2);
				array.append(array3);
				}

			if (shouldCompress)
				{
				BOOST_CHECK(array.usingJudgmentTable());

				BOOST_CHECK_EQUAL(array.judgmentCount(), 2);
				}

			BOOST_CHECK(array.size() == (10+passes) * 8);

			for (long k = 0; k < array.size(); k++)
				{
				bool isNothing = (k%8 == 4 || k%8 == 5);

				if (isNothing)
					BOOST_CHECK(array[k] == nothingIvc);
				else
					BOOST_CHECK(array[k] == intIvc);
				}
			}
	}

BOOST_AUTO_TEST_CASE ( test_jor_from_multiple_threads_is_OK )
	{
	for (long k = 0; k < 10000; k++)
		{
		ForaValueArrayImpl array(&memoryPool);

		array.append(ImplValContainer(CSTValue()));
		array.append(ImplValContainer(CSTValue(false)));
		array.append(ImplValContainer(CSTValue(10)));

		auto runner = [&]() {
			array.currentJor();
			};

		boost::thread t1(runner);
		boost::thread t2(runner);

		t1.join();
		t2.join();
		}
	}

BOOST_AUTO_TEST_CASE ( test_append_random )
	{
	//fuzz test the array, testing all major appending functionality.
	for (long seed = 1; seed < 1000; seed++)
		{
		Ufora::math::Random::Uniform<float> generator(seed);

		ExecutionContextMemoryPool memoryPool(0, memoryManager);

		ForaValueArrayImpl array(&memoryPool);

		ImmutableTreeVector<ImplValContainer> implvals;

		implvals = implvals + ImplValContainer(CSTValue());
		implvals = implvals + ImplValContainer(CSTValue(false));
		implvals = implvals + ImplValContainer(CSTValue(10));

		//we need to have a string allocated on the memory pool in here to catch refcount errors.
		implvals = implvals +
			ImplValContainerUtilities::createString(
				String("this is big enough to be allocated on the heap", &memoryPool)
				);
		implvals = implvals + ImplValContainer(implvals); //a tuple - a bit bigger

		ImmutableTreeVector<ImplValContainer> target;

		const static int maxValues = 20;

		for (long j = 0; j < maxValues; j++)
			{
			if (generator() < .01)
				{
				//append it to itself to test that
				array.append(array);
				target = target + target;
				}

			if (generator() < .01 && array.size() > 2)
				{
				//append part of the array to itself
				long low = generator() * array.size();
				long high = generator() * array.size();
				if (high < low)
					std::swap(low,high);

				array.append(array, low, high);
				target = target + target.slice(low, high);
				}

			long which = implvals.size() * generator();

			//how many times to append
			long count = 1 + generator() * 4;

			for (long z = 0; z < count; z++)
				{
				array.append(
					PackedForaValues(
						JOV::OfType(implvals[which].type()),
						&implvals[which].cast<uint8_t>(),
						1,
						PackedForaValues::strideFor(JOV::OfType(implvals[which].type()))
						)
					);

				target = target + implvals[which];
				}

			if (j + 1 == maxValues || generator() < .02)
				{
				lassert_dump(array.size() == target.size(), "size mismatch for seed " << seed);
				for (long k = 0; k < array.size(); k++)
					lassert_dump(
						array[k] == target[k],
						"item mismatch for seed " << seed << " at slot " << k
						);
				}
			}
		}
	}

BOOST_AUTO_TEST_SUITE_END( )

