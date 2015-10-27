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

#include "FastJORCoverageTable.hppml"
#include "FourLookupHashTableCodegen.hpp"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeTypeForCppml.hpp"
#include "../../Native/TypedNativeLibraryFunction.hpp"

template<>
class NativeTypeForImpl<TypedFora::Abi::FastJORCoverageTable> {
public:
	static NativeType get(void)
		{
		return nativeTypeForCppmlTuple<TypedFora::Abi::FastJORCoverageTable>();
		}
};

template<>
class TypedNativeExpressionBehaviors<TypedFora::Abi::FastJORCoverageTable*> {
public:
	typedef TypedFora::Abi::FourLookupHashTable<uword_t, uword_t, true> table_type;

	TypedNativeExpressionBehaviors(NativeExpression e) : mThis(e)
		{
		}

	TypedNativeExpression<table_type* > lookupTable() const
		{
		return TypedNativeExpression<table_type*>(
			mThis["lookupTable"]
			);
		}

	TypedNativeExpression<JudgmentOnValue> lookup(TypedNativeExpression<JudgmentOnValue> jov) const
		{
		TypedNativeExpression<uword_t> pointerAsWord = jov.forceCast<uword_t>(false);

		TypedNativeVariable<sword_t> slot;

		using namespace TypedNativeExpressionHelpers;

		auto lookupFun = 
				makeTypedNativeLibraryFunction(
					&TypedFora::Abi::FastJORCoverageTable::staticLookup
					);

		return 
			let(slot, lookupTable().slotFor(pointerAsWord),
				if_(slot == (sword_t)-1, 
					lookupFun(
						TypedNativeExpression<TypedFora::Abi::FastJORCoverageTable*>(mThis), 
						jov
						),
					lookupTable().valueForSlot(slot).forceCast<JudgmentOnValue>(false)
					)
				);
		}

private:
	NativeExpression mThis;
};

