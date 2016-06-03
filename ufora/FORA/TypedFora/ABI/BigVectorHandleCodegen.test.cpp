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
#include "BigVectorHandleCodegen.hpp"
#include "BigVectorLayouts.hppml"
#include "ForaValueArray.hppml"
#include "NativeCodeCompilerTestFixture.hpp"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../Core/ExecutionContextImpl.hppml"
#include "../../VectorDataManager/VectorDataMemoryManager.hppml"

using namespace TypedFora::Abi;

class BigVectorHandleCodegenTestFixture : public NativeCodeCompilerTestFixture {
public:
	BigVectorHandleCodegenTestFixture()
		{
		}

	typedef TypedNativeExpression<BigVectorHandle*> big_vector_handle_expr;

	uint8_t* offsetFromPair(TypedFora::Abi::ForaValueArraySlice p, int64_t index)
		{
		if (!p.array())
			return nullptr;
		return p.offsetFor(index);
		}
};

BOOST_FIXTURE_TEST_SUITE( test_TypedFora_Abi_BigVectorHandleCodegen, BigVectorHandleCodegenTestFixture )

BOOST_AUTO_TEST_CASE( test_resizeExpression )
	{
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());

	PolymorphicSharedPtr<VectorDataMemoryManager> memoryManager(
			new VectorDataMemoryManager(scheduler, scheduler)
			);

	ExecutionContextMemoryPool memoryPool(0, memoryManager);

	BigVectorHandle* handle =
		BigVectorHandle::create(&memoryPool, nullptr);

	ForaValueArray* array = ForaValueArray::Empty(&memoryPool);

	array->append(ImplValContainer(CSTValue(10)));

	long offset = 0;

	handle->associateArray(array, offset, IntegerSequence(array->size()), null());

	auto arrayAndOffsetLLVM = compile(&big_vector_handle_expr::sliceForOffset);

	BOOST_CHECK(offsetFromPair(arrayAndOffsetLLVM(handle, offset), offset) == array->offsetFor(0));
	BOOST_CHECK(offsetFromPair(arrayAndOffsetLLVM(handle, offset + 1), offset+1) == nullptr);

	BOOST_CHECK(!handle->sliceForOffset(offset + 1000).array());
	BOOST_CHECK(!arrayAndOffsetLLVM(handle, offset + 1000).array());

	memoryPool.destroy(array);

	memoryPool.destroy(handle);
	}

BOOST_AUTO_TEST_SUITE_END()

