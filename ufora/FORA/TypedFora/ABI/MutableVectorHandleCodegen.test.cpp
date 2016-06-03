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
#include "MutableVectorHandleCodegen.hpp"
#include "../../Core/ImplValContainerUtilities.hppml"
#include "../../Runtime.hppml"
#include "../../Native/NativeCode.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/Logging.hpp"
#include "../JitCompiler/TypedNativeFunctionPointer.hpp"
#include "NativeLayoutType.hppml"
#include "../../VectorDataManager/VectorDataManager.hppml"
#include "../../VectorDataManager/VectorDataMemoryManager.hppml"
#include "../../Core/ImplValContainerUtilities.hppml"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../../core/math/Random.hpp"

using namespace TypedFora::Abi::MutableVectorHandleCodegen;
using TypedFora::Abi::MutableVectorHandle;

class MutableVectorHandleCodegenTestFixture {
public:
	MutableVectorHandleCodegenTestFixture() :
			compiler(Runtime::getRuntime().getTypedForaCompiler()),
			sizeFun(compiler, sizeExpression),
			decrementRefcountFun(compiler, decrementRefcountExpr),
			incrementRefcountFun(compiler, incrementRefcountExpr),
			setItemStringFun(
				compiler,
				boost::bind(
					setItemExpr,
					boost::arg<1>(),
					boost::arg<2>(),
					boost::arg<3>(),
					JudgmentOnValue::OfType(Type::String())
					)
				),
			setItemIvcFun(
				compiler,
				boost::bind(
					setItemExpr,
					boost::arg<1>(),
					boost::arg<2>(),
					boost::arg<3>(),
					JudgmentOnValue()
					)
				),
			getItemStringFun(
				compiler,
				boost::bind(
					getItemExpr,
					boost::arg<1>(),
					boost::arg<2>(),
					JudgmentOnValue::OfType(Type::String())
					)
				),
			getItemIvcFun(
				compiler,
				boost::bind(
					getItemExpr,
					boost::arg<1>(),
					boost::arg<2>(),
					JudgmentOnValue()
					)
				),
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
		lassert(compiler);
		}

	PolymorphicSharedPtr<TypedFora::Compiler> compiler;

	TypedNativeFunctionPointer<size_t (*)(MutableVectorHandle*)> sizeFun;

	TypedNativeFunctionPointer<uint8_t (*)(MutableVectorHandle*)> decrementRefcountFun;

	TypedNativeFunctionPointer<Fora::Nothing (*)(MutableVectorHandle*)> incrementRefcountFun;

	TypedNativeFunctionPointer<Fora::Nothing (*)(MutableVectorHandle*, int64_t, String)>
																			setItemStringFun;

	TypedNativeFunctionPointer<Fora::Nothing (*)(MutableVectorHandle*, int64_t, ImplValContainer)>
																				setItemIvcFun;

	TypedNativeFunctionPointer<String (*)(MutableVectorHandle*, int64_t)> getItemStringFun;
	TypedNativeFunctionPointer<ImplValContainer (*)(MutableVectorHandle*, int64_t)> getItemIvcFun;

	ExecutionContextMemoryPool memoryPool;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_MutableVectorHandleCodegen, MutableVectorHandleCodegenTestFixture )

BOOST_AUTO_TEST_CASE ( test_refcounts )
	{
	MutableVectorHandle* handle = new MutableVectorHandle(&memoryPool, JOV(), hash_type());

	incrementRefcountFun(handle);

	BOOST_CHECK(!decrementRefcountFun(handle));
	BOOST_CHECK(decrementRefcountFun(handle));
	}

BOOST_AUTO_TEST_CASE ( test_instantiate )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	BOOST_CHECK_EQUAL(sizeFun(&handle), 0);
	}

BOOST_AUTO_TEST_CASE ( test_allocate )
	{
	MutableVectorHandle handle(&memoryPool, JOV(), hash_type());

	handle.resize(10, ImplValContainer());

	BOOST_CHECK_EQUAL(sizeFun(&handle), 10);
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

	BOOST_CHECK(sizeFun(&handle) == 10);
	BOOST_CHECK(getItemStringFun(&handle, 4) == aString.cast<String>());

	handle.resize(5, aString);

	BOOST_CHECK(sizeFun(&handle) == 5);
	BOOST_CHECK(getItemStringFun(&handle, 4) == aString.cast<String>());

	handle.resize(10, aDifferentString);

	BOOST_CHECK(sizeFun(&handle) == 10);
	BOOST_CHECK(getItemStringFun(&handle, 4) == aString.cast<String>());
	BOOST_CHECK(getItemStringFun(&handle, 8) == aDifferentString.cast<String>());

	setItemStringFun(&handle, 4, aThirdString.cast<String>());
	BOOST_CHECK(getItemStringFun(&handle, 4) == aThirdString.cast<String>());
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

	BOOST_CHECK(sizeFun(&handle) == 10);
	BOOST_CHECK(getItemIvcFun(&handle, 4) == aString);

	handle.shrink(5);

	handle.setItem(3, anInteger);
	BOOST_CHECK(getItemIvcFun(&handle, 2) == aString);
	BOOST_CHECK(getItemIvcFun(&handle, 3) == anInteger);
	BOOST_CHECK(getItemIvcFun(&handle, 4) == aString);

	handle.resize(10, anInteger);
	BOOST_CHECK(getItemIvcFun(&handle, 4) == aString);
	BOOST_CHECK(getItemIvcFun(&handle, 3) == anInteger);
	BOOST_CHECK(getItemIvcFun(&handle, 8) == anInteger);
	}


BOOST_AUTO_TEST_SUITE_END()


