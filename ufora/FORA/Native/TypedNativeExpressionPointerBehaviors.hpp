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

#include "TypedNativeExpression.fwd.hpp"

template<class T>
class TypedNativeExpressionBuiltinBehaviors<T*, TypedNativeExpressionBehaviorPointerCategory> {
public:
	TypedNativeExpressionBuiltinBehaviors(const NativeExpression& e);

	template<class target_type>
	TypedNativeExpression<target_type> cast() const;

	operator TypedNativeExpression<bool>() const;

	template<class index_type>
	TypedNativeExpression<T> operator[](const TypedNativeExpression<index_type>& e) const;

	TypedNativeExpression<T> operator[](sword_t index) const;

	template<class index_type>
	TypedNativeExpression<T*> operator+(TypedNativeExpression<index_type> e) const;

	TypedNativeExpression<T*> operator+(sword_t index) const;

	TypedNativeExpression<void> store(TypedNativeExpression<T> toStore) const;

private:
	NativeExpression mExpression;
};


