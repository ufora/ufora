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
#include "ForaValueArrayCodegen.hpp"
#include "ForaValueArraySpaceRequirements.hppml"
#include "ForaValueArrayImpl.hppml"
#include "NativeCodeCompilerTestFixture.hpp"
#include "../../Core/ImplValContainerUtilities.hppml"
#include "../../VectorDataManager/VectorDataManager.hppml"
#include "../../VectorDataManager/VectorDataMemoryManager.hppml"
#include "../../Core/ImplValContainerUtilities.hppml"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../../core/math/Random.hpp"
#include "../../../core/threading/CallbackScheduler.hppml"

using namespace TypedFora::Abi::ForaValueArrayCodegen;
using namespace TypedFora::Abi;

class ForaValueArrayCodegenTestFixture : public NativeCodeCompilerTestFixture {
public:
	ForaValueArrayCodegenTestFixture() :
			emptyArray(MemoryPool::getFreeStorePool()),
			arrayWithOneInt(MemoryPool::getFreeStorePool()),
			arrayWithAnIntAndABigTuple(MemoryPool::getFreeStorePool()),
			arrayWithAnIntAndABigTupleCompressed(MemoryPool::getFreeStorePool())
		{
		lassert(compiler);

		arrayWithOneInt.append(ImplValContainer(CSTValue(10)));

		arrayWithAnIntAndABigTuple.append(ImplValContainer(CSTValue(10)));
		arrayWithAnIntAndABigTuple.append(
			ImplValContainerUtilities::createTuple(
				(emptyTreeVec() + ImplValContainer(CSTValue(10))) * 5
				)
			);

		arrayWithAnIntAndABigTupleCompressed.prepareForAppending(
			arrayWithAnIntAndABigTuple.getSpaceRequirements()
			);

		arrayWithAnIntAndABigTupleCompressed.append(arrayWithAnIntAndABigTuple);

		lassert(arrayWithAnIntAndABigTupleCompressed.usingJudgmentTable());
		}

	template<class F1, class F2>
	void checkFunctionImplementation(
				F1 f1,
				F2 f2,
				std::string name
				)
		{
		lassert_dump(
			f1(&emptyArray) == f2(&emptyArray),
			name << " on emptyArray"
			);

		lassert_dump(
			f1(&arrayWithOneInt) == f2(&arrayWithOneInt),
			name << " on arrayWithOneInt"
			);

		lassert_dump(
			f1(&arrayWithAnIntAndABigTuple) == f2(&arrayWithAnIntAndABigTuple),
			name << " on arrayWithAnIntAndABigTuple"
			);
		}

	template<class F1, class F2>
	void checkFunctionImplementationOnValidIndices(
				F1 f1,
				F2 f2,
				std::string name
				)
		{
		checkFunctionImplementationOnValidIndices(
			emptyArray, f1, f2, name + " emptyArray");

		checkFunctionImplementationOnValidIndices(
			arrayWithOneInt, f1, f2, name + " arrayWithOneInt"
			);

		checkFunctionImplementationOnValidIndices(
			arrayWithAnIntAndABigTuple, f1, f2, name + " arrayWithAnIntAndABigTuple"
			);

		checkFunctionImplementationOnValidIndices(
			arrayWithAnIntAndABigTupleCompressed, f1, f2, name + " arrayWithAnIntAndABigTupleCompressed"
			);
		}

	template<class F1, class F2>
	void checkFunctionImplementationOnValidIndices(
			ForaValueArray& array,
			F1 f1,
			F2 f2,
			std::string name
			)
		{
		for (long k = 0; k < array.size(); k++)
			lassert_dump(
				f1(&array, k) == f2(&array, k),
				name << ": " << k
				);
		}

	ForaValueArrayImpl emptyArray;

	ForaValueArrayImpl arrayWithOneInt;

	ForaValueArrayImpl arrayWithAnIntAndABigTuple;

	ForaValueArrayImpl arrayWithAnIntAndABigTupleCompressed;
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_ForaValueArrayCodegen, ForaValueArrayCodegenTestFixture )

BOOST_AUTO_TEST_CASE ( test_layout_is_compatible_with_native_code_assumptions )
	{
	ForaValueArray* array = ForaValueArray::Empty(MemoryPool::getFreeStorePool());

	//we need for the ForaValueArray* to be typecastable to the first value
	//in the ForaValueArrayImpl class to match the assumptions we make in codegen
	BOOST_CHECK_EQUAL((char*)&array->getImpl().mIsWriteable - (char*)array, sizeof(void*));

	MemoryPool::getFreeStorePool()->destroy(array);
	}

BOOST_AUTO_TEST_CASE( test_usingOffsetTableExpression )
	{
	TypedNativeFunctionPointer<bool (*)(ForaValueArray*)> usingOffsetTableLLVM(
		compiler,
		usingOffsetTableExpression
		);

	checkFunctionImplementation(
		[](ForaValueArray* array) { return array->usingOffsetTable(); },
		usingOffsetTableLLVM,
		"usingOffsetTable"
		);
	}

BOOST_AUTO_TEST_CASE( test_sizeExpression )
	{
	TypedNativeFunctionPointer<size_t (*)(ForaValueArray*)> sizeLLVM(
		compiler,
		sizeExpression
		);

	checkFunctionImplementation(
		[](ForaValueArray* array) { return array->size(); },
		sizeLLVM,
		"size"
		);
	}

BOOST_AUTO_TEST_CASE( test_jovExpression )
	{
	TypedNativeFunctionPointer<JudgmentOnValue (*)(ForaValueArray*, int32_t)> jovForLLVM(
		compiler,
		jovForExpression
		);

	checkFunctionImplementationOnValidIndices(
		[](ForaValueArray* array, int32_t index) { return array->jovFor(index); },
		jovForLLVM,
		"jovFor"
		);
	}

BOOST_AUTO_TEST_CASE( test_offsetForExpression )
	{
	TypedNativeFunctionPointer<uint8_t* (*)(ForaValueArray*, size_t)> offsetForLLVM(
		compiler,
		offsetForExpression
		);

	checkFunctionImplementationOnValidIndices(
		[](ForaValueArray* array, size_t index) { return array->offsetFor(index); },
		offsetForLLVM,
		"offsetFor"
		);
	}

BOOST_AUTO_TEST_CASE( test_append_2 )
	{
	ForaValueArrayImpl array(MemoryPool::getFreeStorePool());

	JudgmentOnValue jovInt32 = JudgmentOnValue::OfType(Type::Integer(32, true));
	TypedNativeFunctionPointer<bool (*)(ForaValueArray*, int32_t)>
		appendInt32LLVM(
			compiler,
			boost::bind(
				appendExpression,
				boost::arg<1>(),
				boost::arg<2>(),
				jovInt32
				)
			);

	BOOST_CHECK(!appendInt32LLVM(&array, 13));

	array.append(ImplValContainer(CSTValue("haro")));
	array.append(ImplValContainer(CSTValue(10)));
	array.append(ImplValContainer(CSTValue("haro")));
	array.append(ImplValContainer(CSTValue(10)));
	array.append(ImplValContainer(CSTValue(10)));

	BOOST_CHECK(appendInt32LLVM(&array, 13));

	BOOST_CHECK(array.size() == 6);
	BOOST_CHECK(array[5] == ImplValContainer(CSTValue((int32_t)13)));
	}

BOOST_AUTO_TEST_CASE( test_append_vector )
	{
	ForaValueArrayImpl array(MemoryPool::getFreeStorePool());

	JudgmentOnValue jovVec = jovEmptyVector();

	TypedNativeFunctionPointer<bool (*)(ForaValueArray*, Fora::Nothing)>
		appendEmptyVectorLLVM(
			compiler,
			boost::bind(
				appendExpression,
				boost::arg<1>(),
				boost::arg<2>(),
				jovVec
				)
			);

	BOOST_CHECK(!appendEmptyVectorLLVM(&array, Fora::Nothing()));

	bool OK = false;
	for (long k = 0; k < 10 && !OK; k++)
		{
		array.append(ImplValContainer(CSTValue::blankOf(Type::Vector())));
		if (appendEmptyVectorLLVM(&array, Fora::Nothing()))
			OK = true;
		}

	BOOST_CHECK(OK);
	}

BOOST_AUTO_TEST_CASE( test_append )
	{
	JudgmentOnValue jovInt32 = JudgmentOnValue::OfType(Type::Integer(32, true));
	TypedNativeFunctionPointer<bool (*)(ForaValueArray*, int32_t)>
		appendInt32LLVM(
			compiler,
			boost::bind(
				appendExpression,
				boost::arg<1>(),
				boost::arg<2>(),
				jovInt32
				)
			);

	JudgmentOnValue jovString = JudgmentOnValue::OfType(Type::String());
	TypedNativeFunctionPointer<bool (*)(ForaValueArray*, String)>
		appendStringLLVM(
			compiler,
			boost::bind(
				appendExpression,
				boost::arg<1>(),
				boost::arg<2>(),
				jovString
				)
			);

	JudgmentOnValue jovNothing = JudgmentOnValue::OfType(Type::Nothing());
	TypedNativeFunctionPointer<bool (*)(ForaValueArray*, Fora::Nothing)>
		appendNothingLLVM(
			compiler,
			boost::bind(
				appendExpression,
				boost::arg<1>(),
				boost::arg<2>(),
				jovNothing
				)
			);

	bool someIntsAppended = false;
	bool someStringsAppended = false;
	bool someNothingsAppended = false;

	for (long seed = 1; seed < 1000; seed++)
		{
		Ufora::math::Random::Uniform<float> random(seed);

		ExecutionContextMemoryPool memoryPool(
			0,
			PolymorphicSharedPtr<VectorDataMemoryManager>(
				new VectorDataMemoryManager(
					CallbackScheduler::singletonForTesting(),
					CallbackScheduler::singletonForTesting()
					)
				)
			);

		ImmutableTreeVector<ImplValContainer> appended;

		ForaValueArrayImpl array(&memoryPool);

		for (long valueIx = 0; valueIx < 50; valueIx++)
			{
			//right-skewed number of times to append
			long timesToAppend = 30 * random() * random() * random() + 1;

			long which = random() * 3;

			if (which == 0)
				{
				for (long t = 0; t < timesToAppend; t++)
					{
					String s("this is a pretty big string", &memoryPool);
					if (!appendStringLLVM(&array, s))
						array.append(ImplValContainerUtilities::createString(s));
					else
						someStringsAppended = true;

					appended = appended + ImplValContainerUtilities::createString(s);
					}
				}
				else
			if (which == 1)
				{
				for (long t = 0; t < timesToAppend; t++)
					{
					int32_t value = valueIx;
					if (!appendInt32LLVM(&array, value))
						array.append(ImplValContainer(CSTValue(value)));
					else
						someIntsAppended = true;

					appended = appended + ImplValContainer(CSTValue(value));
					}
				}
			else
				{
				for (long t = 0; t < timesToAppend; t++)
					{
					Fora::Nothing e;

					if (!appendNothingLLVM(&array, e))
						array.append(ImplValContainer());
					else
						someNothingsAppended = true;

					appended = appended + ImplValContainer();
					}
				}
			}

		lassert_dump(appended.size() == array.size(), appended.size() << " != " << array.size());

		for (long j = 0; j < appended.size();j++)
			lassert(appended[j] == array[j]);
		}

	BOOST_CHECK(someIntsAppended);
	BOOST_CHECK(someStringsAppended);
	BOOST_CHECK(someNothingsAppended);
	}



BOOST_AUTO_TEST_SUITE_END()


