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
#include "NativeCode.hppml"
#include "TypedNativeExpressionBehaviorCategories.hpp"
#include "TypedNativeExpressionConstantConversion.hpp"


template<class T>
class TypedNativeExpressionBuiltinBehaviors<T, TypedNativeExpressionBehaviorIntegerCategory> {
public:
	TypedNativeExpressionBuiltinBehaviors(const NativeExpression& e);

	TypedNativeExpressionBuiltinBehaviors(const T& in);

	template<class target_type>
	operator TypedNativeExpression<target_type>() const;

	NativeExpression getExpression() const;

private:
	NativeExpression mExpression;
};

