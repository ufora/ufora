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
#ifndef base_math_Alternative_H_
#define base_math_Alternative_H_

#include "../lassert.hpp"
#include "../serialization/Serialization.hpp"
#include <boost/variant.hpp>

//TODO CLEANUP anybody: get rid of this class and just use boost::variant everywhere.

template<class T1, class T2>
class Alternative {
public:
		typedef T1 left_type;
		typedef T2 right_type;
		Alternative()
			{
			}
		explicit Alternative(const T1& in) : mData(in)
			{
			}
		explicit Alternative(const T2& in) : mData(in)
			{
			}

		template<class T3>
		explicit Alternative(const T3& in) : mData(T2(in))
			{
			}

		~Alternative()
			{
			}
		Alternative(const Alternative<T1, T2>& in) :
				mData(in.mData)
			{
			}
		Alternative& operator=(const Alternative<T1, T2>& in)
			{
			mData = in.mData;

			return *this;
			}
		Alternative& operator=(const T1& in)
			{
			mData = in;

			return *this;
			}
		Alternative& operator=(const T2& in)
			{
			mData = in;

			return *this;
			}
		bool operator==(const Alternative& in) const
			{
			if (isLeft() != in.isLeft())
				return false;
			if (isLeft())
				return in.left() == left();
				else
				return in.right() == right();
			}
		bool operator<(const Alternative& in) const
			{
			if (isLeft() && !in.isLeft())
				return false;
			if (!isLeft() && in.isLeft())
				return true;
			if (isLeft())
				return left() < in.left();
				else
				return right() < in.right();
			}
		template<class T3>
		Alternative& operator=(const T3& in)
			{
			mData = T2(in);

			return *this;
			}
		bool isLeft(void) const
			{
			return boost::get<const T1>(&mData) ? true : false;
			}
		bool isRight(void) const
			{
			return boost::get<const T2>(&mData) ? true : false;
			}
		const T1& left(void) const
			{
			const T1* tr = boost::get<const T1>(&mData);
			lassert(tr);
			return *tr;
			}
		const T2& right(void) const
			{
			const T2* tr = boost::get<const T2>(&mData);
			lassert(tr);
			return *tr;
			}
		 T1& left(void)
			{
			T1* tr = boost::get<T1>(&mData);
			lassert(tr);
			return *tr;
			}
		 T2& right(void)
			{
			T2* tr = boost::get<T2>(&mData);
			lassert(tr);
			return *tr;
			}

private:
		boost::variant<T1, T2> mData;
};

template<class T1, class T2, class storage_type>
class Serializer<Alternative<T1, T2>, storage_type> {
public:
		static void serialize(storage_type& s, const Alternative<T1, T2>& in)
			{
			s.serialize(in.isLeft());
			if (in.isLeft())
				s.serialize(in.left());
				else
				s.serialize(in.right());
			}
};
template<class T1, class T2, class storage_type>
class Deserializer<Alternative<T1, T2>, storage_type> {
public:
		static void deserialize(storage_type& s, Alternative<T1, T2>& in)
			{
			bool isLeft;
			s.deserialize(isLeft);
			if (isLeft)
				{
				T1 t1;
				s.deserialize(t1);
				in = Alternative<T1, T2>(t1);
				}
				else
				{
				T2 t2;
				s.deserialize(t2);
				in = Alternative<T1, T2>(t2);
				}
			}
};


template<class T1>
class Match {
public:
		Match() {}
};

template<class T1, class T2, class TMatch>
bool operator == (const Alternative<T1, T2>& alt, const TMatch& m)
	{
	return false;
	}
template<class T1, class TMatch>
bool operator == (const Alternative<T1, TMatch>& alt, const TMatch& m)
	{
	return alt.isRight() && alt.right() == m;
	}
template<class T1, class TMatch>
bool operator == (const Alternative<TMatch, T1>& alt, const TMatch& m)
	{
	return alt.isLeft() && alt.left() == m;
	}
template<class T1, class T2, class TMatch>
bool operator == (const Alternative<Alternative<T1, T2>, TMatch>& alt, const TMatch& m)
	{
	return alt.isLeft() && alt.left() == m || alt.isRight() && alt.right() == m;
	}
template<class T1, class T2, class TMatch>
bool operator == (const Alternative<TMatch, Alternative<T1, T2> >& alt, const TMatch& m)
	{
	return alt.isLeft() && alt.left() == m || alt.isRight() && alt.right() == m;
	}
template<class T1, class T2, class T3, class T4, class TMatch>
bool operator == (const Alternative<Alternative<T3, T4>, Alternative<T1, T2> >& alt, const TMatch& m)
	{
	return alt.isLeft() && alt.left() == m || alt.isRight() && alt.right() == m;
	}


template<class T1, class T2, class T3, class TMatch>
bool operator == (const Alternative<Alternative<T1, T2>, T3>& alt, const TMatch& m)
	{
	return alt.isLeft() && alt.left() == m;
	}
template<class T1, class T2, class T3, class TMatch>
bool operator == (const Alternative<T3, Alternative<T1, T2> >& alt, const TMatch& m)
	{
	return alt.isRight() && alt.right() == m;
	}



template<class T1, class T2, class TMatch>
bool operator | (const Alternative<T1, T2>& alt, const Match<TMatch>& m)
	{
	return (alt.isLeft() ? (alt.left() |  m) : (alt.right() | m));
	}
template<class T1, class TMatch>
bool operator | (const T1& alt, const Match<TMatch>& m)
	{
	return false;
	}
template<class TMatch>
bool operator | (const TMatch& alt, const Match<TMatch>& m)
	{
	return true;
	}




template<class T1, class T2, class TMatch>
const TMatch& operator || (const Alternative<T1, T2>& alt, const Match<TMatch>& m)
	{
	return (alt.isLeft() ? (alt.left() ||  m) : (alt.right() || m));
	}
template<class T1, class TMatch>
const TMatch& operator || (const T1& alt, const Match<TMatch>& m)
	{
	lassert(false);
	}
template<class TMatch>
const TMatch& operator || (const TMatch& alt, const Match<TMatch>& m)
	{
	return alt;
	}


template<class T1, class T2, class TMatch>
TMatch& operator || (Alternative<T1, T2>& alt, const Match<TMatch>& m)
	{
	return (alt.isLeft() ? (alt.left() ||  m) : (alt.right() || m));
	}
template<class T1, class TMatch>
TMatch& operator || (T1& alt, const Match<TMatch>& m)
	{
	lassert(false);
	}
template<class TMatch>
TMatch& operator || (TMatch& alt, const Match<TMatch>& m)
	{
	return alt;
	}





#endif

