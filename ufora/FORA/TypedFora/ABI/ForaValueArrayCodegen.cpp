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
#include "NativeLayoutType.hppml"
#include "../../Judgment/JudgmentOnValue.hppml"
#include "../../../core/SymbolExport.hpp"
#include "../../../core/Logging.hpp"
#include "../../Native/NativeCode.hppml"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeExpressionBuilder.hppml"
#include "../../Native/TypedNativeExpression.hppml"
#include "../../Native/TypedNativeLibraryFunction.hpp"
#include "DestructorsAndConstructors.hppml"
#include "TypedForaValueTypecasting.hppml"

using TypedFora::Abi::ForaValueArray;

NativeType	NativeTypeForImpl<ForaValueArray>::get()
	{
	NativeType packedValues =
		NativeType::Composite("VTablePtr", NativeType::uword().ptr()) +
		NativeType::Composite("mIsWriteable", NativeType::uword()) +
		NativeType::Composite("mOwningMemoryPool", NativeType::Nothing().ptr()) +
		NativeType::Composite("mDataPtr", NativeType::uint8().ptr()) +
		NativeType::Composite("mBytesReserved", NativeType::uword()) +
		NativeType::Composite("mOffsetTablePtr", NativeType::Integer(8, false).ptr().ptr()) +
		NativeType::Composite("mPerValueOffsetOrOffsetTableCountAllocated", NativeType::uword()) +
		NativeType::Composite("mJudgmentLookupTable", NativeTypeFor<JudgmentOnValue>::get().ptr()) +
		NativeType::Composite("mJudgmentLookupTableSize", NativeType::uword()) +
		NativeType::Composite("mPerValueJudgments", NativeType::Nothing().ptr()) +
		NativeType::Composite("mPerValueJudgmentsAllocated", NativeType::uword()) +
		NativeType::Composite("mValueCount", NativeType::uword());

	return packedValues +
		NativeType::Composite(
			"mPadding",
			NativeType::Array(
				NativeType::Integer(8,false),
				sizeof(ForaValueArray) - packedValues.packedSize()
				)
			)
		;
	}

namespace TypedFora {
namespace Abi {
namespace ForaValueArrayCodegen {

NativeExpression isWriteableExpression(
					const NativeExpression& valueArrayPointerExpr
					)
	{
	lassert(*valueArrayPointerExpr.type() == NativeTypeFor<ForaValueArray>::get().ptr());

	return valueArrayPointerExpr["mIsWriteable"].load();
	}

NativeExpression sizeExpression(
					const NativeExpression& valueArrayPointerExpr
					)
	{
	lassert(*valueArrayPointerExpr.type() == NativeTypeFor<ForaValueArray>::get().ptr());

	return valueArrayPointerExpr["mValueCount"].load();
	}

NativeExpression usingOffsetTableExpression(
					const NativeExpression& valueArrayPointerExpr
					)
	{
	lassert(*valueArrayPointerExpr.type() == NativeTypeFor<ForaValueArray>::get().ptr());

	return
		valueArrayPointerExpr["mOffsetTablePtr"].load().isNotNull();
	}

NativeExpression offsetForExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& indexExpr
					)
	{
	lassert_dump(
		*valueArrayPointerExpr.type() == NativeTypeFor<ForaValueArray>::get().ptr(),
		"Expected ForaValueArray* but got "
			<< prettyPrintString(*valueArrayPointerExpr.type())
		);

	lassert(indexExpr.type()->isInteger());

	return NativeExpression::If(
		usingOffsetTableExpression(valueArrayPointerExpr),
		//use the offset table
		valueArrayPointerExpr["mOffsetTablePtr"].load()[indexExpr].load(),
		//use the stride table
		valueArrayPointerExpr["mDataPtr"].load()
			[valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() * indexExpr]
		);
	}

NativeExpression jovForExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& indexExpr
					)
	{
	lassert(*valueArrayPointerExpr.type() == NativeTypeFor<ForaValueArray>::get().ptr());
	lassert(indexExpr.type()->isInteger());

	return NativeExpression::If(
		valueArrayPointerExpr["mJudgmentLookupTable"].load(),
		NativeExpression::If(
			valueArrayPointerExpr["mJudgmentLookupTableSize"].load() == NativeExpression::ConstantULong(1),
			valueArrayPointerExpr["mJudgmentLookupTable"].load()[0].load(),
			valueArrayPointerExpr["mJudgmentLookupTable"].load()
				[valueArrayPointerExpr["mPerValueJudgments"].load()
					.cast(NativeType::Integer(8,false).ptr(),false)
					[indexExpr].load()
					].load()
			),
		valueArrayPointerExpr["mPerValueJudgments"].load().cast(
			NativeTypeFor<JudgmentOnValue>::get().ptr(),
			false
			)[indexExpr].load()
		);
	}

extern "C" {

BSA_DLLEXPORT
void FORA_clib_foraValueArray_AppendUsingData(
		ForaValueArray* array,
		uint8_t* data,
		const JudgmentOnValue& inJudgment
		)
	{
	array->append(inJudgment, data, 1, 0);
	}

BSA_DLLEXPORT
void FORA_clib_foraValueArray_AppendUsingImplval(
		ForaValueArray* array,
		const ImplValContainer& inIVC
		)
	{
	array->append(inIVC);
	}

}

//a semi-direct fast append occurs when we have per-value judgments allocated, and enough
//room to write directly into the system
NativeExpression isSemiDirectFastAppendableExpression(
					const NativeExpression& valueArrayPointerExpr,
					const JudgmentOnValue& valueJmt
					)
	{
	return
		valueArrayPointerExpr["mJudgmentLookupTableSize"].load().isNull()
			&& valueArrayPointerExpr["mPerValueJudgments"].load().isNotNull()
			&& (valueArrayPointerExpr["mPerValueJudgmentsAllocated"].load() >
					valueArrayPointerExpr["mValueCount"].load())
			&& (
				NativeExpression::If(
					valueArrayPointerExpr["mOffsetTablePtr"].load().isNull(),
					//not using an offset table. make sure we're smaller than the offset!
					( (valueArrayPointerExpr["mValueCount"].load() + NativeExpression::ConstantULong(1)) *
						valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() <=
						valueArrayPointerExpr["mBytesReserved"].load()
						) &&
					valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() >=
						NativeExpression::ConstantULong(PackedForaValues::strideFor(valueJmt))
						,
					//using an offset table, so we need to check that we have both space in the
					//data table and also in the offset table
					((valueArrayPointerExpr["mOffsetTablePtr"].load()
							[valueArrayPointerExpr["mValueCount"].load()].load()[
							NativeExpression::ConstantInt32(PackedForaValues::strideFor(valueJmt))
							]).cast(NativeTypeFor<size_t>::get(), false)
								<=
							(valueArrayPointerExpr["mDataPtr"].load()[
								valueArrayPointerExpr["mBytesReserved"].load()
								])
								.cast(NativeTypeFor<size_t>::get(), false)
							)
					&& (valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() >
						valueArrayPointerExpr["mValueCount"].load())
					)
				);
	}


NativeExpression semiDirectFastAppendExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& dataToAppendExpr,
					const JudgmentOnValue& valueJmt
					)
	{
	lassert(*valueJmt.vectorElementJOV() == valueJmt);

	JOV storageJOV = JudgmentOnValue::OfType(*valueJmt.type());

	//we can directly append this value to the end of the array
	NativeExpressionBuilder builder;

	NativeExpression targetPtr = builder.add(
		NativeExpression::If(
			usingOffsetTableExpression(valueArrayPointerExpr),
			//use the offset table
			valueArrayPointerExpr["mOffsetTablePtr"].load()
				[valueArrayPointerExpr["mValueCount"].load()].load(),
			//use the stride table
			valueArrayPointerExpr["mDataPtr"].load()[
				(valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() *
					valueArrayPointerExpr["mValueCount"].load()).cast(NativeType::int32(), false)
				]
			)
		);

	//store a duplicated copy of the value
	builder.add(
		targetPtr.cast(nativeLayoutType(storageJOV).ptr(), false)
		.store(
			TypedFora::Abi::duplicate(
				dataToAppendExpr,
				valueJmt,
				storageJOV
				)
			)
		);

	//update the judgment table
	builder.add(
		valueArrayPointerExpr["mPerValueJudgments"].load()
			.cast(NativeTypeFor<JudgmentOnValue*>::get(), false)
			[valueArrayPointerExpr["mValueCount"].load()]
			.store(jovAsNativeConstant(valueJmt))
		);

	//increment mValueCount
	builder.add(
		valueArrayPointerExpr["mValueCount"].store(
			valueArrayPointerExpr["mValueCount"].load() +
				NativeExpression::ConstantULong(1)
			)
		);

	//update the offset table
	builder.add(
		NativeExpression::If(
			valueArrayPointerExpr["mOffsetTablePtr"].load().isNotNull(),
			valueArrayPointerExpr["mOffsetTablePtr"].load()
				[valueArrayPointerExpr["mValueCount"].load()]
				.store(targetPtr[NativeExpression::ConstantInt32(PackedForaValues::strideFor(valueJmt))])
				,
			NativeExpression::Nothing()
			)
		);

	return builder(NativeExpression());
	}


//a "direct" fast append occurs when we don't have to do anything but write the value and update
//the count.
NativeExpression isDirectFastAppendableExpression(
					const NativeExpression& valueArrayPointerExpr,
					const JudgmentOnValue& valueJmt
					)
	{
	return
		NativeExpression::If(
			(valueArrayPointerExpr["mJudgmentLookupTableSize"].load() == NativeExpression::ConstantULong(1)),

			(valueArrayPointerExpr["mJudgmentLookupTable"].load().load() == jovAsNativeConstant(valueJmt))
			&&	( (valueArrayPointerExpr["mValueCount"].load() + NativeExpression::ConstantULong(1)) *
					valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load() <=
					valueArrayPointerExpr["mBytesReserved"].load()
					),
			NativeExpression::Constant(NativeConstant::Bool(false))
			);
	}

NativeExpression directFastAppendExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& dataToAppendExpr,
					const JudgmentOnValue& valueJmt
					)
	{
	lassert(valueJmt.type());

	JOV storageJOV = JudgmentOnValue::OfType(*valueJmt.type());

	//we can directly append this value to the end of the array
	NativeExpressionBuilder builder;

	NativeExpression offsetExpr = builder.add(
		valueArrayPointerExpr["mValueCount"].load() *
				valueArrayPointerExpr["mPerValueOffsetOrOffsetTableCountAllocated"].load()
		);

	NativeExpression targetPtr = builder.add(
		valueArrayPointerExpr["mDataPtr"].load()
			[offsetExpr]
		);

	//store a duplicated copy of the value
	builder.add(
		targetPtr.cast(nativeLayoutType(storageJOV).ptr(), false)
			.store(
				TypedFora::Abi::duplicate(
					dataToAppendExpr,
					valueJmt,
					storageJOV
					)
				)
		);

	builder.add(
		valueArrayPointerExpr["mValueCount"].store(
			valueArrayPointerExpr["mValueCount"].load() +
				NativeExpression::ConstantULong(1)
			)
		);

	return builder(NativeExpression());
	}

NativeExpression appendExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& dataToAppendExpr,
					const JudgmentOnValue& valueJmt
					)
	{
	lassert(valueJmt.isValidVectorElementJOV());

	return NativeExpression::If(
		isDirectFastAppendableExpression(valueArrayPointerExpr, valueJmt),
		directFastAppendExpression(valueArrayPointerExpr, dataToAppendExpr, valueJmt) >>
			NativeExpression::Constant(NativeConstant::Bool(true)),
		NativeExpression::If(
			isSemiDirectFastAppendableExpression(valueArrayPointerExpr, valueJmt),
			semiDirectFastAppendExpression(valueArrayPointerExpr, dataToAppendExpr, valueJmt) >>
				NativeExpression::Constant(NativeConstant::Bool(true)),
			NativeExpression::Constant(NativeConstant::Bool(false)),
			.999999
			),
		.999999
		);
	}


}
}
}

