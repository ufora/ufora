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

#include "../../core/Common.hppml"
#include "../../core/Platform.hpp"

//class to control what general behaviors we get
template<class T>
class TypedNativeExpressionBehaviorCategories {
public:
	typedef void result_type;
};

class TypedNativeExpressionBehaviorIntegerCategory {};
class TypedNativeExpressionBehaviorFloatCategory {};
class TypedNativeExpressionBehaviorPointerCategory {};

template<class T>
class TypedNativeExpressionBehaviorCategories<T*> {
public:
	typedef TypedNativeExpressionBehaviorPointerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<float> {
public:
	typedef TypedNativeExpressionBehaviorFloatCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<double> {
public:
	typedef TypedNativeExpressionBehaviorFloatCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<int32_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<int16_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<int64_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<int8_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<uint32_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<uint16_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<uint64_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

template<>
class TypedNativeExpressionBehaviorCategories<uint8_t> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};

#ifdef BSA_PLATFORM_APPLE
template<>
class TypedNativeExpressionBehaviorCategories<long> {
public:
	typedef TypedNativeExpressionBehaviorIntegerCategory result_type;
};
#endif


