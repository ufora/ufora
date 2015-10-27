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
#include "FastJORCoverageTableCodegen.hpp"
#include "NativeCodeCompilerTestFixture.hpp"

using namespace TypedFora::Abi;

class FastJORCoverageTableCodegenTestFixture : public NativeCodeCompilerTestFixture {
public:
	FastJORCoverageTableCodegenTestFixture()
		{
		}

	typedef TypedNativeExpression<FastJORCoverageTable*> table_expr;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_FastJORCoverageTableCodegen, FastJORCoverageTableCodegenTestFixture )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	JudgmentOnValue jovAnything = JOV() ;
	JudgmentOnValue jovTen = JOV::Constant(CSTValue((int32_t)10));
	JudgmentOnValue jovHello = JOV::Constant(CSTValue("hello"));
	JudgmentOnValue jovInteger = JOV::OfType(Type::Integer(32, true));
	JudgmentOnValue jovVectorOfAny = JOV::OfType(Type::Vector());
	JudgmentOnValue jovVectorOfInt = jovVector(JOV::OfType(Type::Integer(32, true)) );
	JudgmentOnValue jovVectorOfString = jovVector(JOV::OfType(Type::String()) );
	

	FastJORCoverageTable table1(
			JudgmentOnResult(emptyTreeSet() + jovInteger + jovVectorOfAny)
			);

	auto lookupLLVM = compile(&table_expr::lookup);

	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovInteger), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovInteger), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovVectorOfInt), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovVectorOfInt), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovVectorOfString), jovVectorOfAny);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovTen), jovInteger);
	BOOST_CHECK_EQUAL_CPPML(lookupLLVM(&table1, jovHello), jovAnything);
	}


BOOST_AUTO_TEST_SUITE_END()


