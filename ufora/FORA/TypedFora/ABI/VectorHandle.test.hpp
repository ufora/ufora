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
#pragma once

#include "VectorHandle.hpp"
#include "ForaValueArray.hppml"
#include "BigVectorPageLayout.test.hpp"
#include "BigVectorHandle.hppml"
#include "BigVectorLayouts.hppml"
#include "../../../core/UnitTest.hpp"
#include "../../../core/threading/CallbackScheduler.hppml"
#include "../../Core/ExecutionContextMemoryPool.hppml"
#include "../../Core/ExecutionContext.hppml"
#include "../../VectorDataManager/PageletTree.hppml"
#include "../../VectorDataManager/VectorDataManager.hppml"
#include "../../VectorDataManager/VectorDataMemoryManager.hppml"

namespace TypedFora {
namespace Abi {

class VectorHandleTestFixture {
public:
	VectorHandleTestFixture() : 
			vdm(	
				new VectorDataManager(
					CallbackScheduler::singletonForTesting(),
					10*1024*1024
					)
				),
			mPagedHandles(vdm->getBigVectorLayouts()),
			mExecutionContext(
					new Fora::Interpreter::ExecutionContext(vdm)
					),

			memoryPool(*mExecutionContext->getExecutionContextMemoryPool())
		{
		}

	VectorHandlePtr newUnpagedHandle(int64_t index, int64_t valueCount)
		{
		ForaValueArray* array = ForaValueArray::Empty(&memoryPool);

		for (int64_t k = 0; k < valueCount; k++)
			array->append(ImplValContainer(CSTValue((int64_t)k)));

		return memoryPool.construct<VectorHandle>(
			Fora::BigVectorId(),
			Fora::PageletTreePtr(),
			array,
			&memoryPool,
			hash_type(index)
			);
		}


	VectorHandlePtr newPagedHandle(int64_t index, ImmutableTreeVector<int64_t> pageSizes)
		{
		BigVectorPageLayout layout = mBigVecTestFixture.getLayout(pageSizes);

		mPagedHandles->registerNewLayout(layout);

		VectorHandle* result = memoryPool.construct<VectorHandle>(
			layout.identity(),
			Fora::PageletTreePtr(),
			(ForaValueArray*)0,
			&memoryPool,
			hash_type(index)
			);

		//result->associatePagedValues(mPagedHandles->getHandle(layout.identity()));

		return result;
		}

	PolymorphicSharedPtr<VectorDataManager> vdm;

	PolymorphicSharedPtr<BigVectorLayouts> mPagedHandles;

	PolymorphicSharedPtr<Fora::Interpreter::ExecutionContext> mExecutionContext;

	ExecutionContextMemoryPool& memoryPool;

	BigVectorPageLayoutTestFixture mBigVecTestFixture;
};

}
}

