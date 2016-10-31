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

#include "../../core/Platform.hpp"
#include "NativeType.hppml"
#include "../../core/containers/ImmutableTreeSet.hppml"
#include "../../core/containers/ImmutableTreeMap.hppml"
#include <type_traits>
#include <set>
#include <map>
#include <vector>

template<class T>
class NativeTypeForImpl {};

#define macro_defineNativeTypeForImpl(T, expr) \
template<> \
class NativeTypeForImpl<T> { \
public:\
	static NativeType get()\
		{\
		return expr;\
		}\
};\

template<class T>
class NativeTypeForImpl<T*> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<T>::get().ptr();
		}
};

template<class T>
class NativeTypeForImpl<volatile T> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<T>::get();
		}
};

template<class T>
class NativeTypeForImpl<ImmutableTreeVector<T> > {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T1, class T2>
class NativeTypeForImpl<std::pair<T1, T2> > {
public:
	static NativeType get()
		{
		return
			NativeType::Composite(NativeTypeForImpl<T1>::get()) +
			NativeType::Composite(NativeTypeForImpl<T2>::get())
			;
		}
};

template<class T>
class NativeTypeForImpl<ImmutableTreeSet<T> > {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T>
class NativeTypeForImpl<std::set<T>*> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T>
class NativeTypeForImpl<std::vector<T>*> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T1, class T2>
class NativeTypeForImpl<std::map<T1, T2>*> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T1, class T2>
class NativeTypeForImpl<ImmutableTreeMap<T1, T2> > {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<void*>::get();
		}
};

template<class T>
class NativeTypeForImpl<const T> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<T>::get();
		}
};

template<class T>
class NativeTypeForImpl<T&> {
public:
	static NativeType get()
		{
		return NativeTypeForImpl<T>::get().ptr();
		}
};

template<>
class NativeTypeForImpl<hash_type> {
public:
	static NativeType get()
		{
		static_assert(sizeof(hash_type) == 5 * sizeof(uint32_t), "hash type layout will be wrong");

		return NativeType::Composite(NativeType::uint32()) +
			NativeType::Composite(NativeType::uint32()) +
			NativeType::Composite(NativeType::uint32()) +
			NativeType::Composite(NativeType::uint32()) +
			NativeType::Composite(NativeType::uint32())
			;
		}
};

macro_defineNativeTypeForImpl(bool, NativeType::Integer(1,false));

macro_defineNativeTypeForImpl(char, NativeType::Integer(8,false));

macro_defineNativeTypeForImpl(uint8_t, NativeType::Integer(8,false));
macro_defineNativeTypeForImpl(int8_t, NativeType::Integer(8,true));

macro_defineNativeTypeForImpl(uint16_t, NativeType::Integer(16,false));
macro_defineNativeTypeForImpl(int16_t, NativeType::Integer(16,true));

macro_defineNativeTypeForImpl(uint32_t, NativeType::Integer(32,false));
macro_defineNativeTypeForImpl(int32_t, NativeType::Integer(32,true));

macro_defineNativeTypeForImpl(uint64_t, NativeType::Integer(64,false));
macro_defineNativeTypeForImpl(int64_t, NativeType::Integer(64,true));

macro_defineNativeTypeForImpl(void, NativeType::Nothing());
macro_defineNativeTypeForImpl(float, NativeType::Float(32));
macro_defineNativeTypeForImpl(double, NativeType::Float(64));

#ifdef BSA_PLATFORM_APPLE
macro_defineNativeTypeForImpl(long, NativeType::Integer(64,true));
macro_defineNativeTypeForImpl(unsigned long, NativeType::Integer(64,false));
#endif

namespace Fora {
	class Nothing;
	class Empty;
};

template<class T>
class NativeTypeFor {
public:
	static NativeType get(void)
		{
		static NativeType* tr = 0;

		if (!tr)
			tr = new NativeType(NativeTypeForImpl<T>::get());
		return *tr;
		}
};

template<>
class NativeTypeFor<void> {
public:
	static NativeType get(void)
		{
		static NativeType* tr = 0;

		if (!tr)
			tr = new NativeType(NativeType::Nothing());

		return *tr;
		}
};

template<>
class NativeTypeForImpl<Fora::Nothing> {
public:
	static NativeType get(void)
		{
		return NativeType::Nothing();
		}
};

template<>
class NativeTypeForImpl<Fora::Empty> {
public:
	static NativeType get(void)
		{
		return NativeType::Nothing();
		}
};


