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

#include "TypedNativeExpressionBehaviorCategories.hpp"

template<class T>
class TypedNativeExpression;

template<class T>
TypedNativeExpression<T> createTypedNativeExpression(const NativeExpression& inExpr);

template<class T>
TypedNativeExpression<T> createTypedNativeExpression(const T& inExpr);


template<class T, class category = typename TypedNativeExpressionBehaviorCategories<T>::result_type>
class TypedNativeExpressionBuiltinBehaviors;

template<class T>
class TypedNativeExpressionBuiltinBehaviors<T, void> {
public:
	TypedNativeExpressionBuiltinBehaviors(const NativeExpression& inExpr)
		{
		}
};

//class for users to override to provide additional codegen functionality
template<class T>
class TypedNativeExpressionBehaviors {
public:
	TypedNativeExpressionBehaviors(const NativeExpression& inExpr)
		{
		}
};

