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

#include <boost/bind.hpp>
#include "PolymorphicSharedPtr.hpp"
#include <boost/mpl/list.hpp>

namespace PolymorphicSharedPtrFuncFromMemberFunc {

template<class T>
T identity(T in) { return in; }

template<typename T, T>
class Wrap;

template<class T, void (T::*fun)()>
class Wrap<void (T::*)(), fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr)
		{
		((*ptr).*fun)();
		}
};

template<class R, class T, R (T::*fun)()>
class Wrap<R (T::*)(), fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr)
		{
		return ((*ptr).*fun)();
		}
};

template<class T, class A1, void (T::*fun)(A1)>
class Wrap<void (T::*)(A1), fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1)
		{
		((*ptr).*fun)(a1);
		}
};

template<class R, class T, class A1, R (T::*fun)(A1)>
class Wrap<R (T::*)(A1), fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1)
		{
		return ((*ptr).*fun)(a1);
		}
};

template<class T, class A1, class A2, void (T::*fun)(A1, A2)>
class Wrap<void (T::*)(A1, A2), fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2)
		{
		((*ptr).*fun)(a1, a2);
		}
};

template<class R, class T, class A1, class A2, R (T::*fun)(A1, A2)>
class Wrap<R (T::*)(A1, A2), fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2)
		{
		return ((*ptr).*fun)(a1, a2);
		}
};

template<class T, class A1, class A2, class A3, void (T::*fun)(A1, A2, A3)>
class Wrap<void (T::*)(A1, A2, A3), fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3)
		{
		((*ptr).*fun)(a1, a2, a3);
		}
};

template<class R, class T, class A1, class A2, class A3, R (T::*fun)(A1, A2, A3)>
class Wrap<R (T::*)(A1, A2, A3), fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3)
		{
		return ((*ptr).*fun)(a1, a2, a3);
		}
};

template<class T, class A1, class A2, class A3, class A4, void (T::*fun)(A1, A2, A3, A4)>
class Wrap<void (T::*)(A1, A2, A3, A4), fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4)
		{
		((*ptr).*fun)(a1, a2, a3, a4);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, R (T::*fun)(A1, A2, A3, A4)>
class Wrap<R (T::*)(A1, A2, A3, A4), fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, void (T::*fun)(A1, A2, A3, A4, A5) >
class Wrap<void (T::*)(A1, A2, A3, A4, A5) , fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, R (T::*fun)(A1, A2, A3, A4, A5) >
class Wrap<R (T::*)(A1, A2, A3, A4, A5) , fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, class A6, void (T::*fun)(A1, A2, A3, A4, A5, A6) >
class Wrap<void (T::*)(A1, A2, A3, A4, A5, A6) , fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5, a6);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, class A6, R (T::*fun)(A1, A2, A3, A4, A5, A6) >
class Wrap<R (T::*)(A1, A2, A3, A4, A5, A6) , fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5, a6);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, void (T::*fun)(A1, A2, A3, A4, A5, A6, A7) >
class Wrap<void (T::*)(A1, A2, A3, A4, A5, A6, A7) , fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5, a6, a7);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, R (T::*fun)(A1, A2, A3, A4, A5, A6, A7) >
class Wrap<R (T::*)(A1, A2, A3, A4, A5, A6, A7) , fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5, a6, a7);
		}
};




template<class T, void (T::*fun)() const>
class Wrap<void (T::*)() const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr)
		{
		((*ptr).*fun)();
		}
};

template<class R, class T, R (T::*fun)() const>
class Wrap<R (T::*)() const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr)
		{
		return ((*ptr).*fun)();
		}
};

template<class T, class A1, void (T::*fun)(A1) const>
class Wrap<void (T::*)(A1) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1)
		{
		((*ptr).*fun)(a1);
		}
};

template<class R, class T, class A1, R (T::*fun)(A1) const>
class Wrap<R (T::*)(A1) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1)
		{
		return ((*ptr).*fun)(a1);
		}
};

template<class T, class A1, class A2, void (T::*fun)(A1, A2) const>
class Wrap<void (T::*)(A1, A2) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2)
		{
		((*ptr).*fun)(a1, a2);
		}
};

template<class R, class T, class A1, class A2, R (T::*fun)(A1, A2) const>
class Wrap<R (T::*)(A1, A2) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2)
		{
		return ((*ptr).*fun)(a1, a2);
		}
};

template<class T, class A1, class A2, class A3, void (T::*fun)(A1, A2, A3) const>
class Wrap<void (T::*)(A1, A2, A3) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3)
		{
		((*ptr).*fun)(a1, a2, a3);
		}
};

template<class R, class T, class A1, class A2, class A3, R (T::*fun)(A1, A2, A3) const>
class Wrap<R (T::*)(A1, A2, A3) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3)
		{
		return ((*ptr).*fun)(a1, a2, a3);
		}
};

template<class T, class A1, class A2, class A3, class A4, void (T::*fun)(A1, A2, A3, A4) const>
class Wrap<void (T::*)(A1, A2, A3, A4) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4)
		{
		((*ptr).*fun)(a1, a2, a3, a4);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, R (T::*fun)(A1, A2, A3, A4) const>
class Wrap<R (T::*)(A1, A2, A3, A4) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, void (T::*fun)(A1, A2, A3, A4, A5) const>
class Wrap<void (T::*)(A1, A2, A3, A4, A5) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, R (T::*fun)(A1, A2, A3, A4, A5) const>
class Wrap<R (T::*)(A1, A2, A3, A4, A5) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, class A6, void (T::*fun)(A1, A2, A3, A4, A5, A6) const>
class Wrap<void (T::*)(A1, A2, A3, A4, A5, A6) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5, a6);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, class A6, R (T::*fun)(A1, A2, A3, A4, A5, A6) const>
class Wrap<R (T::*)(A1, A2, A3, A4, A5, A6) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5, a6);
		}
};

template<class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, void (T::*fun)(A1, A2, A3, A4, A5, A6, A7) const>
class Wrap<void (T::*)(A1, A2, A3, A4, A5, A6, A7) const, fun> {
public:
	static void call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7)
		{
		((*ptr).*fun)(a1, a2, a3, a4, a5, a6, a7);
		}
};

template<class R, class T, class A1, class A2, class A3, class A4, class A5, class A6, class A7, R (T::*fun)(A1, A2, A3, A4, A5, A6, A7) const>
class Wrap<R (T::*)(A1, A2, A3, A4, A5, A6, A7) const, fun> {
public:
	static R call(PolymorphicSharedPtr<T> ptr, A1 a1, A2 a2, A3 a3, A4 a4, A5 a5, A6 a6, A7 a7)
		{
		return ((*ptr).*fun)(a1, a2, a3, a4, a5, a6, a7);
		}
};



}

#define macro_polymorphicSharedPtrFuncFromMemberFunc(x) PolymorphicSharedPtrFuncFromMemberFunc::Wrap<\
	decltype(PolymorphicSharedPtrFuncFromMemberFunc::identity(&x)), &x>::call

#define macro_psp_py_def(s, x) def(s, macro_polymorphicSharedPtrFuncFromMemberFunc(x))

#define macro_psp_py_add_property(s, x) add_property(s, macro_polymorphicSharedPtrFuncFromMemberFunc(x))


