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

#include <stdint.h>
#include "../../Judgment/JudgmentOnValue.hppml"
#include "../../Core/Type.hppml"
#include "../../../core/Common.hppml"
#include "../../../core/serialization/Serialization.hpp"
#include "../../../core/AtomicOps.hpp"
#include "../../../core/SymbolExport.hpp"
#include "../../../core/PolymorphicSharedPtr.hpp"
#include "PackedForaValues.hppml"

namespace TypedFora {
namespace Abi {

class MutableVectorHandle {
public:
	MutableVectorHandle(
		MemoryPool* owningMemoryPool,
		JudgmentOnValue inElementJOV,
		hash_type hash
		);
	
	~MutableVectorHandle();

	size_t size() const { return mSize; }

	JudgmentOnValue elementJOV() const { return mElementJOV; }

	hash_type identityHash() const { return mVectorHash; }

	AO_t refcount() const { return mRefcount; }

	PackedForaValues packedValues() const;

	PackedForaValues appendUninitialized(long count);

	void resize(size_t inTotalElements, const ImplValContainer& inValue);

	void shrink(size_t inTotalElements);

	ImplValContainer operator[](int index) const;

	void setItem(int index, const ImplValContainer& inValue);

	void incrementRefcount();
	
	bool decrementRefcount(); //returns 'true' if we destroyed the object

	//swap the data owned by these two handles. The two handles must have the same identity,
	//types, and must exist in the same memory pool.
	void swapContentsWith(MutableVectorHandle& otherHandle);

private:
	void destroyElements(long start, long stop);

	size_t stride() const;

	AO_t mRefcount;

	size_t mSize;			//how many elements are populated

	uint8_t* mRawDataPtr;	//null only if the vector is empty
	
	MemoryPool* mOwningMemoryPool;	//who owns this MutableVectorHandle?

	JudgmentOnValue mElementJOV;	 	//A judgment on the elements in the vector, which must
									//have a Type.

	hash_type mVectorHash;
};

ostream&	operator<<(ostream& s, MutableVectorHandle* vd);

}
}

