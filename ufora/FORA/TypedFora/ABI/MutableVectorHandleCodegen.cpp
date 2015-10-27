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
#include "NativeLayoutType.hppml"
#include "../../Judgment/JudgmentOnValue.hppml"
#include "../../../core/SymbolExport.hpp"
#include "../../../core/Logging.hpp"
#include "../../Native/NativeCode.hppml"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeExpressionBuilder.hppml"
#include "../../Native/TypedNativeLibraryFunction.hpp"
#include "DestructorsAndConstructors.hppml"

using TypedFora::Abi::MutableVectorHandle;

NativeType	NativeTypeForImpl<MutableVectorHandle>::get()
	{
	return
		NativeType::Composite("mRefcount", NativeType::uword()) +
		NativeType::Composite("mSize", NativeType::uword()) + 
		NativeType::Composite("mRawDataPtr", NativeType::uint8().ptr()) + 
		NativeType::Composite("mOwningMemoryPool", NativeType::Nothing().ptr()) + 
		NativeType::Composite("mElementJOV", NativeTypeFor<JudgmentOnValue>::get()) + 
		NativeType::Composite("mVectorHash", NativeTypeFor<hash_type>::get())
		;
	}

extern "C" {

BSA_DLLEXPORT
void	FORA_clib_incrementMutableVectorHandleRefcount(MutableVectorHandle* handle)
	{
	handle->incrementRefcount();
	}

BSA_DLLEXPORT
uint8_t	FORA_clib_decrementMutableVectorHandleRefcount(MutableVectorHandle* handle)
	{
	return handle->decrementRefcount();
	}
}

namespace TypedFora {
namespace Abi {
namespace MutableVectorHandleCodegen {

NativeExpression sizeExpression(
					const NativeExpression& arrayPtrE
					)
	{
	lassert(*arrayPtrE.type() == NativeTypeFor<MutableVectorHandle>::get().ptr());

	return arrayPtrE["mSize"].load();
	}

NativeExpression incrementRefcountExpr(
					const NativeExpression& arrayPtrE
					)
	{
	lassert(*arrayPtrE.type() == NativeTypeFor<MutableVectorHandle>::get().ptr());

	return makeTypedNativeLibraryFunction(
		&FORA_clib_incrementMutableVectorHandleRefcount
		)(arrayPtrE).getExpression()
		;
	}

NativeExpression decrementRefcountExpr(
					const NativeExpression& arrayPtrE
					)
	{
	lassert(*arrayPtrE.type() == NativeTypeFor<MutableVectorHandle>::get().ptr());
	
	return makeTypedNativeLibraryFunction(
		&FORA_clib_decrementMutableVectorHandleRefcount
		)(arrayPtrE).getExpression()
		;
	}

NativeExpression basePointerExpressionAsRawPtr(
					const NativeExpression& arrayPtrE
					)
	{
	return
		arrayPtrE["mRawDataPtr"]
			.load()
			;
	}


NativeExpression getItemExpr(
					const NativeExpression& arrayPtrE,
					const NativeExpression& indexE,
					const JudgmentOnValue& elementJov
					)
	{
	if (elementJov.constant())
		return NativeExpression();

	return TypedFora::Abi::duplicate(
		elementJov,
		arrayPtrE["mRawDataPtr"]
			.load()
			.cast(nativeLayoutType(elementJov).ptr(), true)
			[indexE].load()
		);
	}

NativeExpression setItemExpr(
					const NativeExpression& arrayPtrE,
					const NativeExpression& indexE,
					const NativeExpression& dataE,
					const JudgmentOnValue& elementJov
					)
	{
	NativeExpressionBuilder builder;

	if (elementJov.constant())
		return NativeExpression();

	NativeExpression eltPtr = builder.add(
		arrayPtrE["mRawDataPtr"].load()
			.cast(nativeLayoutType(elementJov).ptr(), false)
			[indexE]
		);

	NativeExpression duplicatedVal = 
		builder.add(
			TypedFora::Abi::duplicate(elementJov, dataE)
			);

	builder.add(
		TypedFora::Abi::destroy(elementJov, eltPtr.load())
		);

	builder.add(
		eltPtr.store(duplicatedVal)
		);

	return builder(NativeExpression());
	}



}
}
}

