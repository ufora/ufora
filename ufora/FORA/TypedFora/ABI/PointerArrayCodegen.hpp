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

#include "PointerArray.hppml"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeTypeForCppml.hpp"
#include "../../Native/TypedNativeLibraryFunction.hpp"

template<class T>
class NativeTypeForImpl<TypedFora::Abi::PointerArray<T> > {
public:
	static NativeType get(void)
		{
		return nativeTypeForCppmlTuple<TypedFora::Abi::PointerArray<T> >();
		}
};

template<class T>
class TypedNativeExpressionBehaviors<TypedFora::Abi::PointerArray<T>* > {
public:
	TypedNativeExpressionBehaviors(NativeExpression e) : mThis(e)
		{
		}

	TypedNativeExpression<long> count() const
		{
		return TypedNativeExpression<long>(mThis["count"].load());
		}

	TypedNativeExpression<T*> lookup(TypedNativeExpression<long> index) const
		{
		return TypedNativeExpression<T**>(mThis["pointers"].load())[index];
		}

	TypedNativeExpression<void> resize(TypedNativeExpression<long> inCount) const
		{
		auto lookupFun =
				makeTypedNativeLibraryFunction(
					&TypedFora::Abi::PointerArray<T>::resizeStatic
					);

		return lookupFun(
			TypedNativeExpression<TypedFora::Abi::PointerArray<T>*>(mThis),
			inCount
			);
		}

private:
	NativeExpression mThis;
};

