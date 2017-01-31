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

#include "BigVectorPageLayout.hppml"
#include "../../Judgment/JudgmentOnValue.hppml"

namespace TypedFora {
namespace Abi {

class BigVectorPageLayoutTestFixture {
public:
	VectorDataID vdid(int64_t index)
		{
		return
			VectorDataID::Internal(
				Fora::PageId(hash_type(index), 1024, 1024),
				0
				);
		}

	VectorDataIDSlice element(int64_t index, int64_t low, int64_t high, int64_t stride = 1)
		{
		return VectorDataIDSlice(
			vdid(index),
			IntegerSequence(
				(high - low) / stride,
				low,
				stride
				)
			);
		}

	BigVectorPageLayout getLayout(ImmutableTreeVector<int64_t> pageSizes)
		{
		BigVectorPageLayout layout;

		for (int64_t k = 0; k < pageSizes.size(); k++)
			layout = BigVectorPageLayout::concatenate(
				layout,
				BigVectorPageLayout(
					VectorDataIDSlice(
						element(k, 0, pageSizes[k])
						),
					JudgmentOnResult(JOV::OfType(::Type::Integer(64, true))),
					hashValue(pageSizes) + hash_type(k)
					),
				hashValue(pageSizes) + hash_type(k) + hash_type(0)
				);

		return layout;
		}

};


}
}

