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
#include "../TypedFora/ABI/NativeCodeCompilerTestFixture.hpp"
#include "NativeCFGTransforms/Transforms.hppml"

BOOST_FIXTURE_TEST_SUITE( test_NativeCodeResumptionSemantics, TypedFora::Abi::NativeCodeCompilerTestFixture )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	NativeVariable arg = NativeVariable::Temp(NativeType::int64());
	
	NativeVariable arg1 = NativeVariable::Temp(NativeType::int64());
	NativeVariable acc1 = NativeVariable::Temp(NativeType::int64());

	NativeBlockID b1 = NativeBlockID::internal();

	NativeCFG cfg(
		emptyTreeVec() + NativeType::int64(),
		emptyTreeMap() + 
			NativeBlockID::entry() + 
			NativeBlock(
				emptyTreeVec() + arg,
				NativeExpression::JumpToResumption(b1, 
					emptyTreeMap() + arg1 + arg.expr() + acc1 + NativeExpression::ConstantInt64(0)
					)
				) + 
			NativeBlockID::external(1) + 
			NativeBlock(
				emptyTreeVec() + arg1 + acc1,
				NativeExpression::Resumption(b1, NativeExpression::SideEffectfulNoOp(), NativeExpression::Nothing()) >> 
				NativeExpression::If(
					arg1.expr() > NativeExpression::ConstantInt64(0),
					NativeExpression::Jump(
						NativeBlockID::external(1),
						emptyTreeVec() + 
							(arg1.expr() + NativeExpression::ConstantInt64(-1)) + 
							(acc1.expr() + arg1.expr())
						),
					NativeExpression::Return(0, acc1.expr())
					)
				)
		);

	TypedNativeFunctionPointer<int64_t (*)(int64_t)> f(compiler, cfg);

	BOOST_CHECK(f(3) == 6);
	}

BOOST_AUTO_TEST_SUITE_END()


