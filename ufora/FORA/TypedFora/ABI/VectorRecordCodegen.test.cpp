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
#include "VectorRecord.hpp"
#include "VectorHandle.test.hpp"
#include "NativeCodeCompilerTestFixture.hpp"
#include "VectorRecordCodegen.hppml"
#include <type_traits>

using namespace TypedFora::Abi;

class VectorRecordCodegenTestFixture :
				public VectorHandleTestFixture,
				public NativeCodeCompilerTestFixture
{
public:
	VectorRecordCodegenTestFixture()
		{
		}

	typedef TypedNativeExpression<TypedFora::Abi::VectorRecord> record_expr;

	static record_expr incrementAndReturn(record_expr e)
		{
		return e.incrementRefcount() >> e.self();
		}
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_VectorRecordCodegen, VectorRecordCodegenTestFixture )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	TypedFora::Abi::VectorRecord record(this->newUnpagedHandle(0, 10));

	BOOST_CHECK(compile(&record_expr::size)(record) == 10);

	BOOST_CHECK(compile(&record_expr::dataPtr)(record) == record.dataPtr());

	BOOST_CHECK(compile(&record_expr::unpagedValues)(record) == record.dataPtr()->unpagedValues());

	BOOST_CHECK(compile(&incrementAndReturn)(record) == record);
	}

BOOST_AUTO_TEST_CASE( test_empty )
	{
	BOOST_CHECK(compile(&record_expr::empty)() == TypedFora::Abi::VectorRecord());
	}

BOOST_AUTO_TEST_CASE( test_index_and_offset_unpaged )
	{
	TypedFora::Abi::VectorRecord record(this->newUnpagedHandle(0, 10));

	BOOST_CHECK(
		compile(&record_expr::arrayAndOffsetForWithFakeCallbacks)(record, 0) ==
			(pair<TypedFora::Abi::ForaValueArray*, int64_t>(record.unpagedValues(), 0))
		);

	BOOST_CHECK(
		compile(&record_expr::arrayAndOffsetForWithFakeCallbacks)(record, 9) ==
			(pair<TypedFora::Abi::ForaValueArray*, int64_t>(record.unpagedValues(), 9))
		);
	}

BOOST_AUTO_TEST_CASE( test_index_and_offset_paged )
	{
	TypedFora::Abi::VectorRecord record(this->newPagedHandle(0, ImmutableTreeVector<int64_t>() + 10));

	BOOST_CHECK(
		compile(&record_expr::arrayAndOffsetForWithFakeCallbacks)(record, 0) ==
			(pair<TypedFora::Abi::ForaValueArray*, int64_t>(
				nullptr,
				0
				)
			)
		);
	}


TypedNativeExpression<bool>
				appendInt64Expression(
					TypedNativeExpression<TypedFora::Abi::VectorRecord> vecExpr,
					TypedNativeExpression<int64_t> intExpr
					)
	{
	return vecExpr.appendAssumingAppendableAndPooled(
		intExpr.getExpression(),
		JOV::OfType(Type::Integer(64, true))
		);
	}



BOOST_AUTO_TEST_CASE( test_appending )
	{
	TypedFora::Abi::VectorRecord record(this->newUnpagedHandle(0, 11));
	TypedFora::Abi::VectorRecord record2(record.dataPtr(), 9, 0, 1);

	BOOST_CHECK(compile(&record_expr::isAppendable)(record));
	BOOST_CHECK(!compile(&record_expr::isAppendable)(record2));

	BOOST_CHECK(compile(appendInt64Expression)(record, 23));

	BOOST_CHECK(!compile(&record_expr::isAppendable)(record));
	}


BOOST_AUTO_TEST_SUITE_END()

