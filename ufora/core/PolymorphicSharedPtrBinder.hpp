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

namespace PolymorphicSharedPtrBinder {

template<class T>
class ExtractWeakPtrAndCall0 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)())
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)();
		}
};

template<class T, class A1>
class ExtractWeakPtrAndCall1 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1), A1 a1)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)(a1);
		}
};

template<class T, class A1, class A2>
class ExtractWeakPtrAndCall2 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2), A1 a1, A2 a2)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)(a1, a2);
		}
};

template<class T, class A1, class A2, class A3>
class ExtractWeakPtrAndCall3 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3), A1 a1, A2 a2, A3 a3)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)(a1, a2, a3);
		}
};

template<class T, class A1, class A2, class A3, class A4>
class ExtractWeakPtrAndCall4 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3, A4), A1 a1, A2 a2, A3 a3, A4 a4)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)(a1, a2, a3, a4);
		}
};


template<class T, class A1, class A2, class A3, class A4, class A5>
class ExtractWeakPtrAndCall5 {
public:
	static void call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3, A4, A5), A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return;

		( (*ptr).*fun)(a1, a2, a3, a4, a5);
		}
};


template<class T>
boost::function1<void, PolymorphicSharedWeakPtr<T> >
memberFunctionToWeakPtrFunction(void (T::* in)())
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall0<T>::call,
		_1,
		in
		);
	}

template<class T, class A1>
boost::function2<void, PolymorphicSharedWeakPtr<T>, A1>
memberFunctionToWeakPtrFunction(void (T::* in)(A1))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall1<T, A1>::call,
		_1,
		in,
		_2
		);
	}

template<class T, class A1, class A2>
boost::function3<void, PolymorphicSharedWeakPtr<T>, A1, A2>
memberFunctionToWeakPtrFunction(void (T::* in)(A1, A2))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall2<T, A1, A2>::call,
		_1,
		in,
		_2,
		_3
		);
	}

template<class T, class A1, class A2, class A3>
boost::function4<void, PolymorphicSharedWeakPtr<T>, A1, A2, A3>
memberFunctionToWeakPtrFunction(void (T::* in)(A1, A2, A3))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall3<T, A1, A2, A3>::call,
		_1,
		in,
		_2,
		_3,
		_4
		);
	}

template<class T, class A1, class A2, class A3, class A4>
boost::function5<void, PolymorphicSharedWeakPtr<T>, A1, A2, A3, A4>
memberFunctionToWeakPtrFunction(void (T::* in)(A1, A2, A3, A4))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall4<T, A1, A2, A3, A4>::call,
		_1,
		in,
		_2,
		_3,
		_4,
		_5
		);
	}

template<class T, class A1, class A2, class A3, class A4, class A5>
boost::function6<void, PolymorphicSharedWeakPtr<T>, A1, A2, A3, A4, A5>
memberFunctionToWeakPtrFunction(void (T::* in)(A1, A2, A3, A4, A5))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCall5<T, A1, A2, A3, A4, A5>::call,
		_1,
		in,
		_2,
		_3,
		_4,
		_5,
		_6
		);
	}






















template<class T>
class ExtractWeakPtrAndCallOrReturnFalse0 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)())
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)();

		return true;
		}
};

template<class T, class A1>
class ExtractWeakPtrAndCallOrReturnFalse1 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1), A1 a1)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)(a1);

		return true;
		}
};

template<class T, class A1, class A2>
class ExtractWeakPtrAndCallOrReturnFalse2 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2), A1 a1, A2 a2)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)(a1, a2);

		return true;
		}
};

template<class T, class A1, class A2, class A3>
class ExtractWeakPtrAndCallOrReturnFalse3 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3), A1 a1, A2 a2, A3 a3)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)(a1, a2, a3);

		return true;
		}
};

template<class T, class A1, class A2, class A3, class A4>
class ExtractWeakPtrAndCallOrReturnFalse4 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3, A4), A1 a1, A2 a2, A3 a3, A4 a4)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)(a1, a2, a3, a4);

		return true;
		}
};


template<class T, class A1, class A2, class A3, class A4, class A5>
class ExtractWeakPtrAndCallOrReturnFalse5 {
public:
	static bool call(PolymorphicSharedWeakPtr<T> weakPtr, void (T::* fun)(A1, A2, A3, A4, A5), A1 a1, A2 a2, A3 a3, A4 a4, A5 a5)
		{
		PolymorphicSharedPtr<T> ptr = weakPtr.lock();
		if (!ptr)
			return false;

		( (*ptr).*fun)(a1, a2, a3, a4, a5);

		return true;
		}
};


template<class T>
boost::function1<bool, PolymorphicSharedWeakPtr<T> >
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)())
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse0<T>::call,
		_1,
		in
		);
	}

template<class T, class A1>
boost::function2<bool, PolymorphicSharedWeakPtr<T>, A1>
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)(A1))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse1<T, A1>::call,
		_1,
		in,
		_2
		);
	}

template<class T, class A1, class A2>
boost::function3<bool, PolymorphicSharedWeakPtr<T>, A1, A2>
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)(A1, A2))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse2<T, A1, A2>::call,
		_1,
		in,
		_2,
		_3
		);
	}

template<class T, class A1, class A2, class A3>
boost::function4<bool, PolymorphicSharedWeakPtr<T>, A1, A2, A3>
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)(A1, A2, A3))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse3<T, A1, A2, A3>::call,
		_1,
		in,
		_2,
		_3,
		_4
		);
	}

template<class T, class A1, class A2, class A3, class A4>
boost::function5<bool, PolymorphicSharedWeakPtr<T>, A1, A2, A3, A4>
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)(A1, A2, A3, A4))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse4<T, A1, A2, A3, A4>::call,
		_1,
		in,
		_2,
		_3,
		_4,
		_5
		);
	}

template<class T, class A1, class A2, class A3, class A4, class A5>
boost::function6<bool, PolymorphicSharedWeakPtr<T>, A1, A2, A3, A4, A5>
memberFunctionToWeakPtrFunctionOrReturnFalse(void (T::* in)(A1, A2, A3, A4, A5))
	{
	using namespace boost;

	return boost::bind(
		ExtractWeakPtrAndCallOrReturnFalse5<T, A1, A2, A3, A4, A5>::call,
		_1,
		in,
		_2,
		_3,
		_4,
		_5,
		_6
		);
	}

}
