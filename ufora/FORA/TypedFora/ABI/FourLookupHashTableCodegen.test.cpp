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
#include "FourLookupHashTableCodegen.hpp"
#include "../../Runtime.hppml"
#include "../../Native/NativeCode.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/Logging.hpp"
#include "../JitCompiler/TypedNativeFunctionPointer.hpp"
#include "NativeLayoutType.hppml"

using namespace TypedFora::Abi;

class FourLookupHashTableCodegenTestFixture {
public:
	FourLookupHashTableCodegenTestFixture() : 
			compiler(Runtime::getRuntime().getTypedForaCompiler()),
			sizeLLVM(
				compiler,
				sizeExpression
				),
			containsLLVM(
				compiler,
				containsExpression
				),
			insertLLVM(
				compiler,
				insertExpression
				)
		{
		lassert(compiler);
		}
	
	typedef FourLookupHashTable<long, long, false> table_type;
	
	static NativeExpression sizeExpression(NativeExpression e)
		{
		return TypedNativeExpression<table_type*>(e).size().getExpression();
		}
	
	static NativeExpression containsExpression(NativeExpression e, NativeExpression key)
		{
		return TypedNativeExpression<table_type*>(e).contains(
			TypedNativeExpression<long>(key)
			).getExpression();
		}

	static NativeExpression insertExpression(
								NativeExpression e, 
								NativeExpression key, 
								NativeExpression value
								)
		{
		return TypedNativeExpression<table_type*>(e).insert(
			TypedNativeExpression<long>(key),
			TypedNativeExpression<long>(value)
			).getExpression();
		}

	PolymorphicSharedPtr<TypedFora::Compiler> compiler;

	TypedNativeFunctionPointer<size_t (*)(table_type*)> sizeLLVM;
	TypedNativeFunctionPointer<bool (*)(table_type*, long)> containsLLVM;
	TypedNativeFunctionPointer<void (*)(table_type*, long, long)> insertLLVM;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_FourLookupHashTableCodegen, FourLookupHashTableCodegenTestFixture )


BOOST_AUTO_TEST_CASE( test_basic )
	{
	boost::shared_ptr<table_type> table(new table_type());
	(*table)[10] = 11;

	BOOST_CHECK(sizeLLVM(table.get()) == 1);
	BOOST_CHECK(containsLLVM(table.get(), 10) == true);
	BOOST_CHECK(containsLLVM(table.get(), 11) == false);

	insertLLVM(table.get(), 11, 100);
	BOOST_CHECK(containsLLVM(table.get(), 11) == true);

	for (long k = 12; k < 50; k++)
		{
		insertLLVM(table.get(), k, 100);
		BOOST_CHECK(containsLLVM(table.get(), k) == true);
		}
	}


BOOST_AUTO_TEST_SUITE_END()


