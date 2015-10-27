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
#ifndef base_math_Nullable_H_
#define base_math_Nullable_H_

#include "../lassert.hpp"
#include <boost/optional.hpp>

#include "../serialization/Serialization.fwd.hpp"
#include "../cppml/CPPMLPrettyPrinter.fwd.hppml"
#include "../cppml/CPPMLEquality.fwd.hppml"
#include "../cppml/CPPMLVisit.fwd.hppml"


class null {
public:
		null()
			{
			}
};
class nullRef {
public:
		nullRef()
			{
			}
};


template<class T>
class Nullable {
public:
		Nullable()
			{
			}
		Nullable(null in)
			{
			}
		explicit Nullable(const T& in) : mData(in)
			{
			}
		Nullable(const Nullable<T>& in) :
				mData(in.mData)
			{
			}
		Nullable& operator=(null in)
			{
			mData = boost::optional<T>();
			return *this;
			}
		Nullable& operator=(const Nullable<T>& in)
			{
			mData = in.mData;

			return *this;
			}
		Nullable& operator=(const T& in)
			{
			mData.reset(in);

			return *this;
			}

		operator bool() const
			{
			return mData;
			}

		inline const T*	operator->() const
			{
			strong_assert(mData);
			return &*mData;
			}
		inline T*	operator->()
			{
			strong_assert(mData);
			return &*mData;
			}
		inline const T&	operator*() const
			{
			strong_assert(mData);
			return *mData;
			}
		inline T&	operator*()
			{
			strong_assert(mData);
			return *mData;
			}
		bool operator<(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this < *other;
			if ( !(*this) && !other)
				return false;
			return (bool)other;
			}
		bool operator==(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this == *other;
			if ( !(*this) && !other)
				return true;
			return false;
			}
		bool operator!=(const Nullable<T>& other) const
			{
			return !(*this == other);
			}
		bool operator>(const Nullable<T>& other) const
			{
			return other < *this;
			}
		bool operator<=(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this <= *other;
			if ( !(*this) && !other)
				return true;
			return (bool)other;
			}
		bool operator>=(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this >= *other;
			if ( !(*this) && !other)
				return true;
			return !(bool)other;
			}

		bool isNull(void) const
			{
			return !isValue();
			}
		bool isValue(void) const
			{
			return (bool)(*this);
			}
		typedef Nullable<T> ValueType;
		typedef Nullable<T> self_type;

		const ValueType& getValue(void) const
			{
			return *this;
			}

		typedef T	member_0_type;
		const T& getM0(void) const { return *mData; }

private:
		boost::optional<T> mData;
};

template<class T, class storage_type>
class Serializer<Nullable<T>, storage_type> {
public:
		static void serialize(storage_type& s, const Nullable<T>& in)
			{
			bool is = in;
			s.serialize(is);
			if (is)
				s.serialize(*in);
			}
};
template<class T, class storage_type>
class Deserializer<Nullable<T>, storage_type> {
public:
		static void deserialize(storage_type& s, Nullable<T>& out)
			{
			bool n;
			s.deserialize(n);
			if (n)
				{
				T t;
				s.deserialize(t);
				out = t;
				}
				else
				out = null();
			}
};

template<class T>
class Nullable<const T&> {
public:
		Nullable()
			{
			mData = 0;
			}
		Nullable(null in) : mData(0)
			{
			}
		explicit Nullable(const T& in) : mData(&in)
			{
			}
		Nullable(const Nullable<const T&>& in) :
				mData(in.mData)
			{
			}
		Nullable& operator=(null in)
			{
			mData = 0;
			return *this;
			}
		Nullable& operator=(const Nullable<const T&>& in)
			{
			mData = in.mData;

			return *this;
			}
		Nullable& operator=(const T& in)
			{
			mData = &in;

			return *this;
			}

		operator bool() const
			{
			return mData;
			}

		inline const T*	operator->() const
			{
			strong_assert(mData);
			return mData;
			}
		inline const T&	operator*() const
			{
			strong_assert(mData);
			return *mData;
			}
		bool operator<(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this < *other;
			if ( !(*this) && !other)
				return false;
			return (bool)other;
			}
		bool operator==(const Nullable<T>& other) const
			{
			if ( (*this) && other)
				return **this == *other;
			if ( !(*this) && !other)
				return true;
			return false;
			}

		//interface to CPPML match construct
		bool isNull(void) const
			{
			return !mData;
			}
		bool isValue(void) const
			{
			return mData;
			}
		typedef Nullable<const T&> ValueType;
		typedef Nullable<const T&> self_type;

		const ValueType& getValue(void) const
			{
			return *this;
			}

		typedef T	member_0_type;
		const T& getM0(void) const { return *mData; }

private:
		const T* mData;
};

template<class T>
Nullable<T> makeNullable(const T& in)
	{
	return Nullable<T>(in);
	}
template<class T>
const Nullable<T>& makeNullable(const Nullable<T>& in)
	{
	return in;
	}

template<class T>
Nullable<T> operator<<(null n, const T& t)
	{
	return Nullable<T>(t);
	}

template<class T>
Nullable<const T&> operator<<(nullRef n, const T& t)
	{
	return Nullable<const T&>(t);
	}

template<class T>
class CPPMLPrettyPrint<Nullable<T> > {
public:
		static void prettyPrint(CPPMLPrettyPrintStream& s, const Nullable<T>& t)
			{
			if (t)
				streamTo(s, *t);
				else
				streamTo(s, "<null>");
			}
};

template<class T>
class CPPMLEquality<Nullable<T>, void> {
public:
		static char cmp(const Nullable<T>& lhs, const Nullable<T>& rhs)
			{
			if (!lhs && !rhs)
				return 0;
			if (!lhs && rhs)
				return -1;
			if (lhs && !rhs)
				return 1;
			return cppmlCmp(*lhs, *rhs);
			}
};

template<class T>
class CPPMLVisit<Nullable<T>, void> {
public:
		template<class F>
		static void apply(const Nullable<T>& in, F& f)
			{
			if (in)
				visit(*in, f);
			}
};

template<class T>
class CPPMLVisitWithIndex<Nullable<T>, void> {
public:
		template<class F, class F2>
		static void apply(const Nullable<T>& in, F& f, const F2& inF2)
			{
			if (in)
				visit(*in, f, inF2);
			}
};


#endif

