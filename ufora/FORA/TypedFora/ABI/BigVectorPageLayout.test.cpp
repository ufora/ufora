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
#include "BigVectorPageLayout.hppml"
#include "BigVectorPageLayout.test.hpp"
#include "../../../core/Logging.hpp"
#include "../../../core/UnitTest.hpp"
#include "../../../core/UnitTestCppml.hpp"

using namespace TypedFora::Abi;


BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_BigVectorPageLayout, BigVectorPageLayoutTestFixture )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	JudgmentOnResult jor1(JudgmentOnValue::OfType(Type::Integer(64, false)));

	BigVectorPageLayout id1(element(0, 0, 1000), jor1, hash_type());
	BigVectorPageLayout id2(element(1, 0, 1000), jor1, hash_type());

	BOOST_CHECK(id1.size() == 1000);
	BOOST_CHECK(id2.size() == 1000);

	BigVectorPageLayout id3 = BigVectorPageLayout::concatenate(id1, id2, hash_type());
	id3.validateInternalState();

	BOOST_CHECK(id3.size() == 2000);

	BOOST_CHECK(id3.slicesCoveringRange(0,1000) == emptyTreeVec() + element(0,0,1000));
	BOOST_CHECK(id3.slicesCoveringRange(500,1000) == emptyTreeVec() + element(0,500,1000));
	BOOST_CHECK(id3.slicesCoveringRange(500,1500) ==
								emptyTreeVec() + element(0,500,1000) + element(1,0,500));

	BOOST_CHECK(id3.slicesCoveringRange(1000, 2000) ==
								emptyTreeVec() + element(1,0,1000));

	BOOST_CHECK(id3.slicesCoveringRange(1000, 1500) ==
								emptyTreeVec() + element(1,0,500));

	BOOST_CHECK(id3.slicesCoveringRange(1200, 1500) ==
								emptyTreeVec() + element(1,200,500));

	BOOST_CHECK(id3.pageAtIndex(0) == element(0, 0, 1000).vector().getPage());
	BOOST_CHECK(id3.pageAtIndex(50) == element(0, 0, 1000).vector().getPage());
	BOOST_CHECK(id3.pageAtIndex(1000) == element(1, 0, 1000).vector().getPage());
	BOOST_CHECK(id3.pageAtIndex(1050) == element(1, 0, 1000).vector().getPage());
	BOOST_CHECK(id3.pageAtIndex(1999) == element(1, 0, 1000).vector().getPage());

	id3.slice(0, 1000, hash_type()).validateInternalState();
	id3.slice(500, 1000, hash_type()).validateInternalState();
	id3.slice(500, 1500, hash_type()).validateInternalState();
	id3.slice(0, 2000, hash_type()).validateInternalState();
	}

BOOST_AUTO_TEST_CASE( test_slicing )
	{
	JudgmentOnResult jor1(JudgmentOnValue::OfType(Type::Integer(64, false)));

	BigVectorPageLayout id1(element(0, 0, 1), jor1, hash_type());
	BigVectorPageLayout id2(element(0, 1, 2), jor1, hash_type());
	BigVectorPageLayout id3(element(1, 0, 1), jor1, hash_type());
	BigVectorPageLayout id4(element(1, 1, 2), jor1, hash_type());

	BigVectorPageLayout id =
		BigVectorPageLayout::concatenate(
			BigVectorPageLayout::concatenate(id1, id2, hash_type()),
			BigVectorPageLayout::concatenate(id3, id4, hash_type()),
			hash_type()
			);

	id.validateInternalState();

	BOOST_CHECK_EQUAL_CPPML(id.slice(0,1, hash_type()), id1);
	BOOST_CHECK_EQUAL_CPPML(id.slice(1,2, hash_type()), id2);
	BOOST_CHECK_EQUAL_CPPML(id.slice(2,3, hash_type()), id3);
	BOOST_CHECK_EQUAL_CPPML(id.slice(3,4, hash_type()), id4);
	}

BOOST_AUTO_TEST_CASE( test_sliceAndConcat )
	{
	JudgmentOnResult jor1(JudgmentOnValue::OfType(Type::Integer(64, false)));

	BigVectorPageLayout id(element(0, 0, 1000), jor1, hash_type());

	id.validateInternalState();

	BigVectorPageLayout id1 = id.slice(0, 500, hash_type());
	BigVectorPageLayout id2 = id.slice(500, 1000, hash_type());

	BigVectorPageLayout id3 = BigVectorPageLayout::concatenate(id1, id2, hash_type());

	BOOST_CHECK_EQUAL_CPPML(id, id3);
	}

BOOST_AUTO_TEST_SUITE_END()

