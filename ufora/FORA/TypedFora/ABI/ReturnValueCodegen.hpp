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

#include "../../Axioms/ReturnValue.hpp"
#include "../../Native/NativeTypeFor.hpp"
#include "../../Native/NativeTypeForCppml.hpp"
#include "../../Native/TypedNativeLibraryFunction.hpp"


template<class T>
class NativeTypeForImpl;

template<class A0, class A1, class A2, class A3, class A4, class A5>
class NativeTypeForImpl<Fora::ReturnValue<A0, A1, A2, A3, A4, A5> > {
public:
	static NativeType get(void)
		{
		return NativeType::Composite(NativeTypeFor<uint64_t>::get()) + 
			NativeType::Composite(
				NativeType::Array(
					NativeTypeFor<uint8_t>::get(),
					sizeof(Fora::ReturnValue<A0, A1, A2, A3, A4, A5>) - sizeof(uint64_t)
					)
				);
		}
};




template<class A0, class A1, class A2, class A3, class A4, class A5>
class TypedNativeExpressionBehaviors<Fora::ReturnValue<A0, A1, A2, A3, A4, A5> > {
public:
	TypedNativeExpressionBehaviors(NativeExpression e) : mThis(e)
		{
		}

	TypedNativeExpression<uint64_t> getIndex() const
		{
		return TypedNativeExpression<uint64_t>(mThis[0]);
		}

	TypedNativeExpression<A0> get0() const
		{
		return TypedNativeExpression<A0>(
			mThis[1].cast(NativeTypeFor<A0>::get(), true)
			);
		}

	TypedNativeExpression<A1> get1() const
		{
		return TypedNativeExpression<A1>(
			mThis[1].cast(NativeTypeFor<A1>::get(), true)
			);
		}

	TypedNativeExpression<A2> get2() const
		{
		return TypedNativeExpression<A2>(
			mThis[1].cast(NativeTypeFor<A2>::get(), true)
			);
		}

	TypedNativeExpression<A3> get3() const
		{
		return TypedNativeExpression<A3>(
			mThis[1].cast(NativeTypeFor<A3>::get(), true)
			);
		}

	TypedNativeExpression<A4> get4() const
		{
		return TypedNativeExpression<A4>(
			mThis[1].cast(NativeTypeFor<A4>::get(), true)
			);
		}

	TypedNativeExpression<A5> get5() const
		{
		return TypedNativeExpression<A5>(
			mThis[1].cast(NativeTypeFor<A5>::get(), true)
			);
		}

private:
	NativeExpression mThis;
};

