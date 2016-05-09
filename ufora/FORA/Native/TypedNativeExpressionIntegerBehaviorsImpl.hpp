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

#include "TypedNativeExpressionIntegerBehaviors.hpp"

template<class T, class category = typename TypedNativeExpressionBehaviorCategories<T>::result_type>
class TypedNativeIntegerCastExpression {};

template<class T>
class TypedNativeIntegerCastExpression<T, TypedNativeExpressionBehaviorIntegerCategory> {
public:
	static TypedNativeExpression<T> call(NativeExpression e)
		{
		return createTypedNativeExpression<T>(
			e.cast(NativeTypeFor<T>::get(), false)
			);
		}
};

inline TypedNativeExpression<bool> operator||(
						TypedNativeExpression<bool> lhs,
						TypedNativeExpression<bool> rhs
						)
	{
	return TypedNativeExpression<bool>(
		lhs.getExpression() || rhs.getExpression()
		);
	}

inline TypedNativeExpression<bool> operator&&(
						TypedNativeExpression<bool> lhs,
						TypedNativeExpression<bool> rhs
						)
	{
	return TypedNativeExpression<bool>(
		lhs.getExpression() && rhs.getExpression()
		);
	}


template<class T>
TypedNativeExpression<T> operator +(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs + TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<T> operator -(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs - TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<T> operator *(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs * TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<T> operator /(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory> rhs(other);
	return lhs / rhs;
	}

template<class T>
TypedNativeExpression<T> operator %(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs % TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator ==(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const T& other)
	{
	return lhs == TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator !=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs != TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator <(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs < TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator >(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs > TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator <=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs <= TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<bool> operator >=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, T other)
	{
	return lhs >= TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>(other);
	}

template<class T>
TypedNativeExpression<T> operator +(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<T>(
		NativeExpression::BinaryOp(
			NativeBinaryOpcode::Add(),
			lhs.getExpression(),
			other.getExpression()
			)
		);
	}

template<class T>
TypedNativeExpression<T> operator -(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<T>(
		NativeExpression::BinaryOp(
			NativeBinaryOpcode::Sub(),
			lhs.getExpression(),
			other.getExpression()
			)
		);
	}

template<class T>
TypedNativeExpression<T> operator /(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<T>(
		NativeExpression::BinaryOp(
			NativeBinaryOpcode::Div(),
			lhs.getExpression(),
			other.getExpression()
			)
		);
	}

template<class T>
TypedNativeExpression<T> operator *(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<T>(
		NativeExpression::BinaryOp(
			NativeBinaryOpcode::Mul(),
			lhs.getExpression(),
			other.getExpression()
			)
		);
	}

template<class T>
TypedNativeExpression<T> operator %(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<T>(
		NativeExpression::BinaryOp(
			NativeBinaryOpcode::Mod(),
			lhs.getExpression(),
			other.getExpression()
			)
		);
	}

template<class T>
TypedNativeExpression<bool> operator ==(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() == other.getExpression());
	}

template<class T>
TypedNativeExpression<bool> operator !=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() != other.getExpression());
	}

template<class T>
TypedNativeExpression<bool> operator <=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() >= other.getExpression());
	}

template<class T>
TypedNativeExpression<bool> operator >=(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() >= other.getExpression());
	}

template<class T>
TypedNativeExpression<bool> operator <(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() < other.getExpression());
	}

template<class T>
TypedNativeExpression<bool> operator >(const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& lhs, const TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>& other)
	{
	return createTypedNativeExpression<bool>(lhs.getExpression() > other.getExpression());
	}


template<class T>
TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>
			::TypedNativeExpressionBuiltinBehaviors(const NativeExpression& e) : mExpression(e)
	{

	}

template<class T>
TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>::
	TypedNativeExpressionBuiltinBehaviors(const T& in) :
			mExpression(TypedNativeExpressionConstantConversion<T>::get(in))
	{

	}

template<class T>
template<class target_type>
TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>::
		operator TypedNativeExpression<target_type>() const
	{
	return TypedNativeIntegerCastExpression<target_type>::call(mExpression);
	}


template<class T>
NativeExpression
TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory>
			::getExpression() const
	{
	return mExpression;
	}


