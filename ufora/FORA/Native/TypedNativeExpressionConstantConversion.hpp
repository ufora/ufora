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

#include "NativeCode.hppml"
#include "../../core/Platform.hpp"

template<class T>
class TypedNativeExpressionConstantConversion {
public:
};

template<class T>
class TypedNativeExpressionConstantConversion<T*> {
public:
	static NativeExpression get(T* in)
		{
		return NativeExpression::Constant(NativeConstant::VoidPtr((uword_t)in))
			.cast(NativeTypeFor<T*>::get(), false);
		}
};



template<>
class TypedNativeExpressionConstantConversion<bool> {
public:
	static NativeExpression get(bool in)
		{
		return NativeExpression::Constant(NativeConstant::Bool(in));
		}
};

template<>
class TypedNativeExpressionConstantConversion<int8_t> {
public:
	static NativeExpression get(int8_t in)
		{
		return NativeExpression::Constant(NativeConstant::Int8(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<uint8_t> {
public:
	static NativeExpression get(uint8_t in)
		{
		return NativeExpression::Constant(NativeConstant::UInt8(in));
		}
};

template<>
class TypedNativeExpressionConstantConversion<int16_t> {
public:
	static NativeExpression get(int16_t in)
		{
		return NativeExpression::Constant(NativeConstant::Int16(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<uint16_t> {
public:
	static NativeExpression get(uint16_t in)
		{
		return NativeExpression::Constant(NativeConstant::UInt16(in));
		}
};

template<>
class TypedNativeExpressionConstantConversion<int32_t> {
public:
	static NativeExpression get(int32_t in)
		{
		return NativeExpression::Constant(NativeConstant::Int32(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<uint32_t> {
public:
	static NativeExpression get(uint32_t in)
		{
		return NativeExpression::Constant(NativeConstant::UInt32(in));
		}
};

template<> class TypedNativeExpressionConstantConversion<int64_t> {
public:
	static NativeExpression get(int64_t in)
		{
		return NativeExpression::Constant(NativeConstant::Int64(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<uint64_t> {
public:
	static NativeExpression get(uint64_t in)
		{
		return NativeExpression::Constant(NativeConstant::UInt64(in));
		}
};


template<>
class TypedNativeExpressionConstantConversion<float> {
public:
	static NativeExpression get(float in)
		{
		return NativeExpression::Constant(NativeConstant::Float(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<double> {
public:
	static NativeExpression get(double in)
		{
		return NativeExpression::Constant(NativeConstant::Double(in));
		}
};

#ifdef BSA_PLATFORM_APPLE
template<>
class TypedNativeExpressionConstantConversion<long> {
public:
	static NativeExpression get(long in)
		{
		return NativeExpression::Constant(NativeConstant::Int64(in));
		}
};
template<>
class TypedNativeExpressionConstantConversion<unsigned long> {
public:
	static NativeExpression get(unsigned long in)
		{
		return NativeExpression::Constant(NativeConstant::UInt64(in));
		}
};
#endif


