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

#include "TypedNativeExpressionPointerBehaviors.hpp"


template<class T>
class TypedNativePointerCastExpression {};

template<class T>
class TypedNativePointerCastExpression<T*> {
public:
	static TypedNativeExpression<T*> call(NativeExpression e)
		{
		return createTypedNativeExpression<T*>(
			e.cast(NativeTypeFor<T*>::get(), false)
			);
		}
};

template<>
class TypedNativePointerCastExpression<uword_t> {
public:
	static TypedNativeExpression<uword_t> call(NativeExpression e)
		{
		return createTypedNativeExpression<uword_t>(
			e.cast(NativeTypeFor<uword_t>::get(), false)
			);
		}
};

template<class T, class index_type, 
	class behavior = typename TypedNativeExpressionBehaviorCategories<index_type>::result_type>
class TypedNativePointerIndexExpression;

template<class T, class index_type>
class TypedNativePointerIndexExpression<T*, index_type, TypedNativeExpressionBehaviorIntegerCategory> {
public:
	static TypedNativeExpression<T> call(NativeExpression e, TypedNativeExpression<index_type> index)
		{
		return createTypedNativeExpression<T>(
			e[index.getExpression()].load()
			);
		}
};

template<class T, class index_type, 
	class behavior = typename TypedNativeExpressionBehaviorCategories<index_type>::result_type>
class TypedNativePointerArithmeticExpression;

template<class T, class index_type>
class TypedNativePointerArithmeticExpression<T*, index_type, TypedNativeExpressionBehaviorIntegerCategory> {
public:
	static TypedNativeExpression<T*> call(NativeExpression e, TypedNativeExpression<index_type> index)
		{
		return createTypedNativeExpression<T*>(
			e[index.getExpression()]
			);
		}
};



template<class T>
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		TypedNativeExpressionBuiltinBehaviors(const NativeExpression& e) : mExpression(e)
	{

	}

template<class T>
template<class target_type>
TypedNativeExpression<target_type> 
		TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::cast() const
	{
	return TypedNativePointerCastExpression<target_type>::call(mExpression);
	}

template<class T>
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		operator TypedNativeExpression<bool>() const
	{
	return TypedNativeExpression<bool>(mExpression.isNotNull());
	}

template<class T>
template<class index_type>
TypedNativeExpression<T> 
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		operator[](const TypedNativeExpression<index_type>& e) const
	{
	return TypedNativePointerIndexExpression<T*, index_type>::call(mExpression, e);
	}

template<class T>
TypedNativeExpression<T> 
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		operator[](sword_t index) const
	{
	return (*this)[TypedNativeExpression<sword_t>(index)];
	}

template<class T>
template<class index_type>
TypedNativeExpression<T*> 
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		operator+(TypedNativeExpression<index_type> e) const
	{
	return TypedNativePointerArithmeticExpression<T*, index_type>::call(mExpression, e);
	}

template<class T>
TypedNativeExpression<T*> 
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		operator+(sword_t index) const
	{
	return (*this)[TypedNativeExpression<sword_t>(index)];
	}

template<class T>
TypedNativeExpression<void> 
TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory>::
		store(TypedNativeExpression<T> toStore) const
	{
	return TypedNativeExpression<void>(
		mExpression.store(toStore.getExpression())
		);
	}


