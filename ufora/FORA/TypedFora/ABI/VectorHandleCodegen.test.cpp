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
#include "VectorHandle.test.hpp"
#include "NativeCodeCompilerTestFixture.hpp"
#include "../../Native/TypedNativeExpression.hppml"
#include "VectorHandleCodegen.hppml"

using namespace TypedFora::Abi;

class VectorHandleCodegenTestFixture : 
				public VectorHandleTestFixture,
				public NativeCodeCompilerTestFixture 
{
public:
	VectorHandleCodegenTestFixture()
		{
		}

	typedef TypedNativeExpression<TypedFora::Abi::VectorHandle*> handle_expr;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_VectorHandleCodegen, VectorHandleCodegenTestFixture )

BOOST_AUTO_TEST_CASE( test_instantiate )
	{
	TypedFora::Abi::VectorHandlePtr handle = newUnpagedHandle(0, 10);

	compile(&handle_expr::incrementRefcount)(handle.ptr());

	BOOST_CHECK(compile(&handle_expr::size)(handle.ptr()) == 10);

	compile(&handle_expr::decrementRefcount)(handle.ptr());
	}

BOOST_AUTO_TEST_SUITE_END()

