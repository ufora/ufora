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

#include "BigVectorHandle.hppml"
#include "PointerArray.hppml"
#include "PointerArrayCodegen.hpp"
#include "SimplePODArray.hppml"
#include "SimplePODArrayCodegen.hpp"
#include "ForaValueArraySlice.hppml"
#include "ForaValueArraySliceCodegen.hppml"
#include "BigVectorHandleFixedSizeCacheCodegen.hppml"
#include "ForaValueArrayCodegen.hpp"
#include "BigVectorPageLayoutCodegen.hppml"
#include "NativeLayoutType.hppml"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeTypeForCppml.hpp"
#include "../../Native/TypedNativeLibraryFunction.hpp"

template<>
class NativeTypeForImpl<TypedFora::Abi::BigVectorHandle> {
public:
	static NativeType get(void)
		{
		return nativeTypeForCppmlTuple<TypedFora::Abi::BigVectorHandle>();
		}
};

template<>
class NativeTypeForImpl<TypedFora::Abi::BigVectorHandleMappedSlices*> {
public:
	static NativeType get(void)
		{
		return NativeTypeFor<void*>::get();
		}
};

template<>
class TypedNativeExpressionBehaviors<TypedFora::Abi::BigVectorHandle*> {
public:
	TypedNativeExpressionBehaviors(NativeExpression e) : mThis(e)
		{
		}

	typedef TypedFora::Abi::BigVectorHandle big_vector_handle_type;

	typedef TypedFora::Abi::BigVectorHandleFixedSizeCache lookup_slot_type;

	TypedNativeExpression<lookup_slot_type*> fixedSizeCache() const
		{
		return TypedNativeExpression<lookup_slot_type*>(
			mThis["fixedSizeCache"]
			);
		}

	TypedNativeExpression<big_vector_handle_type*> self() const
		{
		return TypedNativeExpression<big_vector_handle_type*>(mThis);
		}

	TypedNativeExpression<pair<TypedFora::Abi::ForaValueArray*, int64_t> >
						arrayAndOffsetFor(TypedNativeExpression<int64_t> index) const
		{
		TypedNativeVariable<TypedFora::Abi::ForaValueArraySlice> slice;

		using namespace TypedNativeExpressionHelpers;

		return let(
			slice, 
			this->sliceForOffset(index),
			TypedNativeExpression<pair<TypedFora::Abi::ForaValueArray*, int64_t> >::create(
				slice.array(),
				slice.mapIndex(index)
				)
			);
		}

	TypedNativeExpression<TypedFora::Abi::ForaValueArraySlice> sliceForOffset(
													TypedNativeExpression<int64_t> offset
													) const
		{
		TypedNativeVariable<TypedFora::Abi::BigVectorHandleFixedSizeCache> fixedSizeCacheVar;

		TypedNativeVariable<int64_t> offsetWithinArray;

		using namespace TypedNativeExpressionHelpers;

		return 
			let(fixedSizeCacheVar, fixedSizeCache()[0],
			if_(fixedSizeCacheVar.firstContains(offset), 
				fixedSizeCacheVar.slice1(), 
				if_(fixedSizeCacheVar.secondContains(offset), 
					fixedSizeCacheVar.slice2(), 
					makeTypedNativeLibraryFunction(
						&TypedFora::Abi::BigVectorHandle::retrieveSlice
						)(self(), offset),
					.999999
					),
				.999999
				)
			);
		}

private:
	NativeExpression mThis;
};

