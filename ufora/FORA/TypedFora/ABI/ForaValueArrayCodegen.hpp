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

#include "ForaValueArray.hppml"

class NativeType;
class NativeExpression;

template<class T>
class NativeTypeForImpl;

template<>
class NativeTypeForImpl<TypedFora::Abi::ForaValueArray> {
public:
	static NativeType get(void);
};

class JudgmentOnResult;

namespace TypedFora {
namespace Abi {
namespace ForaValueArrayCodegen {

//equivalent to 'valueArrayPointerExpr->usingOffsetTable()'
NativeExpression usingOffsetTableExpression(
					const NativeExpression& valueArrayPointerExpr
					);

//equivalent to 'valueArrayPointerExpr->isWriteable()'
NativeExpression isWriteableExpression(
					const NativeExpression& valueArrayPointerExpr
					);

//equivalent to 'valueArrayPointerExpr->size()'
NativeExpression sizeExpression(
					const NativeExpression& valueArrayPointerExpr
					);

//equivalent to 'valueArrayPointerExpr->offsetFor(indexExpr)'
NativeExpression offsetForExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& indexExpr
					);

NativeExpression jovForExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& indexExpr
					);

//equivalent to 'valueArrayPointerExpr->isWriteableAndFastAppendable()'
NativeExpression isWriteableAndFastAppendable(
					const NativeExpression& valueArrayPointerExpr
					);

//returns an expression that appends 'dataToAppend' to the value array and returns 'true'
//if it's possible to do so in a binary. Otherwise, it returns false and clients must
//fall back to a libcall.
NativeExpression appendExpression(
					const NativeExpression& valueArrayPointerExpr,
					const NativeExpression& dataToAppendExpr,
					const JudgmentOnValue& valueJmt
					);


}
}
}
