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

/*************

ReturnValue

Allows Fora axioms to represent multiple control flow return type paths in a single alternative.

e.g.

ReturnValue<Nothing, int, String> f(int x)
	{
	if (x == 0)
		return Fora::slot0(Nothing());
	if (x == 1)
		return Fora::slot1(10);
	if (x == 2)
		return Fora::slot2(String("hello"));
	}

******************/

#include "../../core/IntegerTypes.hpp"
#include "../../core/lassert.hpp"
#include "../Native/NativeTypeFor.hpp"
#include "../Core/Nothing.hpp"

namespace TypedFora {
namespace Abi {

class VectorLoadRequest;

}
}

namespace Fora {

template<class T, int index>
class IndexedReturnValue {
public:
	IndexedReturnValue(const T& in) : m(in)
		{
		}

	const T& get() const
		{
		return m;
		}

private:
	T m;
};

template<int index>
class IndexedReturnValueConstructor {
public:
	template<class T>
	IndexedReturnValue<T, index> operator()(const T& in) const
		{
		return IndexedReturnValue<T, index>(in);
		}
};

class Empty {};

template<class T>
class IsEmptyType {
public:
	const static bool result = false;
};

template<>
class IsEmptyType<Empty> {
public:
	const static bool result = true;
};

template<class T>
class IsVectorLoadType {
public:
	const static bool result = false;
};

template<>
class IsVectorLoadType<TypedFora::Abi::VectorLoadRequest> {
public:
	const static bool result = true;
	};

namespace {

	IndexedReturnValueConstructor<0> slot0;
	IndexedReturnValueConstructor<1> slot1;
	IndexedReturnValueConstructor<2> slot2;
	IndexedReturnValueConstructor<3> slot3;
	IndexedReturnValueConstructor<4> slot4;
	IndexedReturnValueConstructor<5> slot5;

}

template<class A0, class A1 = Empty, class A2 = Empty, class A3 = Empty, class A4 = Empty, class A5 = Empty>
class ReturnValue {
public:
	ReturnValue()
		{
		mWhich = 0;
		new ((A0*)mData) A0();
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 0>& in)
		{
		mWhich = 0;
		new ((A0*)mData) A0(in.get());
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 1>& in)
		{
		mWhich = 1;
		new ((A1*)mData) A1(in.get());
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 2>& in)
		{
		mWhich = 2;
		new ((A2*)mData) A2(in.get());
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 3>& in)
		{
		mWhich = 3;
		new ((A3*)mData) A3(in.get());
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 4>& in)
		{
		mWhich = 4;
		new ((A4*)mData) A4(in.get());
		}

	template<class T>
	ReturnValue(const IndexedReturnValue<T, 5>& in)
		{
		mWhich = 5;
		new ((A5*)mData) A5(in.get());
		}

	class Destroy {
	public:
		template<class T>
		void operator()(T& toDestroy) const
			{
			toDestroy.~T();
			}
	};

	class Duplicate {
	public:
		Duplicate(char* target) : mTarget(target)
			{
			}

		template<class T>
		void operator()(const T& toCopy)
			{
			new ((T*)mTarget) T(toCopy);
			}

	private:
		char* mTarget;
	};

	~ReturnValue()
		{
		Destroy destroyer;

		this->visit(destroyer);
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 0>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 0;
		new ((A0*)mData) A0(in.get());

		return *this;
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 1>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 1;
		new ((A1*)mData) A1(in.get());

		return *this;
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 2>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 2;
		new ((A2*)mData) A2(in.get());

		return *this;
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 3>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 3;
		new ((A3*)mData) A3(in.get());

		return *this;
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 4>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 4;
		new ((A4*)mData) A4(in.get());

		return *this;
		}

	template<class T>
	ReturnValue& operator=(const IndexedReturnValue<T, 5>& in)
		{
		Destroy destroyer;

		visit(destroyer);

		mWhich = 5;
		new ((A5*)mData) A5(in.get());
		}

	ReturnValue(const ReturnValue& in)
		{
		Duplicate duplicator(mData);

		in.visit(duplicator);

		mWhich = in.mWhich;
		}

	ReturnValue& operator=(const ReturnValue& in)
		{
		if (this == &in)
			return *this;

		Destroy destroyer;

		visit(destroyer);

		Duplicate duplicator(mData);

		in.visit(duplicator);

		mWhich = in.mWhich;

		return *this;
		}

	uint64_t getIndex() const
		{
		return mWhich;
		}

	const A0& get0() const
		{
		lassert(mWhich == 0);

		return *(const A0*)mData;
		}

	const A1& get1() const
		{
		lassert(mWhich == 1);
		return *(const A1*)mData;
		}

	const A2& get2() const
		{
		lassert(mWhich == 2);
		return *(const A2*)mData;
		}

	const A3& get3() const
		{
		lassert(mWhich == 3);
		return *(const A3*)mData;
		}

	const A4& get4() const
		{
		lassert(mWhich == 4);
		return *(const A4*)mData;
		}

	const A5& get5() const
		{
		lassert(mWhich == 5);
		return *(const A5*)mData;
		}

	A0& get0()
		{
		lassert(mWhich == 0);

		return *( A0*)mData;
		}

	A1& get1()
		{
		lassert(mWhich == 1);
		return *( A1*)mData;
		}

	A2& get2()
		{
		lassert(mWhich == 2);
		return *( A2*)mData;
		}

	A3& get3()
		{
		lassert(mWhich == 3);
		return *( A3*)mData;
		}

	A4& get4()
		{
		lassert(mWhich == 4);
		return *( A4*)mData;
		}

	A5& get5()
		{
		lassert(mWhich == 5);
		return *( A5*)mData;
		}

	template<class visitor>
	void visit(visitor& v)
		{
		if (mWhich == 0)
			v(get0());
		else if (mWhich == 1)
			v(get1());
		else if (mWhich == 2)
			v(get2());
		else if (mWhich == 3)
			v(get3());
		else if (mWhich == 4)
			v(get4());
		else if (mWhich == 5)
			v(get5());
		else
			{
			lassert_dump(false, mWhich);
			}
		}

	template<class visitor>
	void visit(visitor& v) const
		{
		if (mWhich == 0)
			v(get0());
		else if (mWhich == 1)
			v(get1());
		else if (mWhich == 2)
			v(get2());
		else if (mWhich == 3)
			v(get3());
		else if (mWhich == 4)
			v(get4());
		else if (mWhich == 5)
			v(get5());
		else
			{
			lassert_dump(false, mWhich);
			}
		}

private:
	uint64_t mWhich;

	//this will always have 8 byte alignment
	const static uint32_t sz0 = sizeof(A0);
	const static uint32_t sz1 = sizeof(A1) > sz0 ? sizeof(A1) : sz0;
	const static uint32_t sz2 = sizeof(A2) > sz1 ? sizeof(A2) : sz1;
	const static uint32_t sz3 = sizeof(A3) > sz2 ? sizeof(A3) : sz2;
	const static uint32_t sz4 = sizeof(A4) > sz3 ? sizeof(A4) : sz3;
	const static uint32_t sz5 = sizeof(A5) > sz4 ? sizeof(A5) : sz4;

	//round up to nearest 8 bytes
	const static uint32_t finalSz = sz5 % 8 ? sz5 + (8 - sz5 % 8) : sz5;

	char mData[finalSz];
};

}




