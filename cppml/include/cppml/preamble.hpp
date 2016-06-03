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
namespace CPPML {

class Kinds {
public:
		class tuple {};
		class alternative {};
};

//our version of 'remove_reference'
template<typename _Tp>
struct remove_reference { typedef _Tp   type; };

template<typename _Tp>
struct remove_reference<_Tp&> { typedef _Tp   type; };

template<typename _Tp>
struct remove_reference<_Tp&&> { typedef _Tp   type; };

//our version of 'remove_constness'
template<typename _Tp>
struct remove_constness { typedef _Tp   type; };

template<typename _Tp>
struct remove_constness<const _Tp> { typedef _Tp   type; };


//our version of forward, which we need because we don't have 'std' included here
template<class S>
S&& forward(typename ::CPPML::remove_reference<S>::type& a) /* noexcept - remove when gcc stops choking on it*/
	{
	return static_cast<S&&>(a);
	}

//our version of move, which we need because we don't ahve 'std' here
template<class T>
typename ::CPPML::remove_reference<T>::type&& move(T&& a) /* noexcept - remove when gcc stops choking on it*/
	{
	typedef typename ::CPPML::remove_reference<T>::type&& RvalRef;
	return static_cast<RvalRef>(a);
	}


class Null {};

class CircularMemoError { };

template<class self_type, class default_t>
class Refcount {
public:
		typedef unsigned long refcount_type;
		static void increment(refcount_type& ioR)
			{
			ioR++;
			};
		static bool decrement(refcount_type& ioR)
			{
			if (ioR == 1)
				{
				ioR--;
				return true;
				}
				else
				{
				ioR--;
				return false;
				}
			}
		};

/************************************
Basic prototype for a "Memo" object.

Clients who write

	@type AType =
		-| ...
	with
		T x = (expr)

will implement an instance of MemoStorage<AType, T, void> to
control how the memo is calculated.
************************************/

template<class self_type, class held_type, class default_t>
class MemoStorage {
public:
	MemoStorage() :
			mMemoizedValue(0),
			mStatus(0)
		{
		}

	~MemoStorage()
		{
		if (mMemoizedValue)
			delete mMemoizedValue;
		}

	const static char kValid = 1;
	const static char kComputing = 2;
	const static char kCircular = 3;

	template<class getter_type>
	const held_type& get(const getter_type& getter)
		{
		if (mStatus == kValid)
			return *mMemoizedValue;

		if (mStatus == kComputing || mStatus == kCircular)
			throw CircularMemoError();

		mStatus = kComputing;

		try {
			mMemoizedValue = new held_type(getter());
			}
		catch(CircularMemoError& circularMemo)
			{
			mStatus = kCircular;
			throw circularMemo;
			}

		mStatus = kValid;

		return *mMemoizedValue;
		}

private:
	char mStatus;

	held_type* mMemoizedValue;
};

template<class tagged_union_type, class common_type, class data_type, class default_t = void>
class TaggedUnion;

//Base class for tagged unions. Holds a refcount and some common data.
template<class tagged_union_type, class in_common_type, class default_t = void>
class TaggedUnionBase {
public:
		typedef typename tagged_union_type::tag_type tag_type;

		typedef in_common_type common_type;

		TaggedUnionBase(tag_type inTag, const common_type& in) :
				tag(inTag),
				common(in),
				refcount(1)
			{
			}

		typedef typename Refcount<tagged_union_type, void>::refcount_type refcount_type;

		refcount_type refcount;
		common_type common;

		tag_type tag;

		void incrementRefcount(void)
			{
			Refcount<tagged_union_type, default_t>::increment(refcount);
			}

		bool decrementRefcount(void)
			{
			return Refcount<tagged_union_type, default_t>::decrement(refcount);
			}

		unsigned long getRefcount(void) const
			{
			return refcount;
			}
};

//Layout type for a specific tagged union that holds 'data_type' as the specific data
template<class tagged_union_type, class in_common_type, class in_data_type, class default_t>
class TaggedUnion : public TaggedUnionBase<tagged_union_type, in_common_type, default_t> {
public:
		typedef typename tagged_union_type::tag_type tag_type;

		typedef in_data_type data_type;

		typedef in_common_type common_type;


		template<class arg_common_type, class arg_data_type>
		TaggedUnion(tag_type tag, arg_common_type&& inCommon, arg_data_type&& inData) :
				TaggedUnionBase<tagged_union_type, common_type, default_t>(
					tag,
					::CPPML::move(inCommon)
					),
				data(::CPPML::move(inData))
			{
			}
		data_type	data;
};


//how we hold references to cppml base classes
template<class cppml_type, class default_t>
class TaggedUnionReference {
public:
		typedef typename cppml_type::common_data_type common_data_type;

		typedef ::CPPML::TaggedUnionBase<cppml_type, common_data_type>
			tagged_union_base_type;

		typedef TaggedUnionReference<cppml_type, default_t> self_type;

		TaggedUnionReference(tagged_union_base_type* inPointedTo) : mPointedTo(inPointedTo)
			{
			}
		TaggedUnionReference() : mPointedTo()
			{
			}

		bool	valid(void)
			{
			return mPointedTo;
			}

		tagged_union_base_type*	mPointedTo;

		typename cppml_type::tag_type	getTag() const
			{
			return mPointedTo->tag;
			}
		common_data_type& getCommonData() const
			{
			return mPointedTo->common;
			}

		template<class subtype>
		void destroyAs(subtype* deliberatelyNullPtr)
			{
			delete static_cast<
				::CPPML::TaggedUnion<cppml_type, common_data_type, subtype>*
				>(mPointedTo);
			mPointedTo = 0;
			}

		template<class subtype>
		subtype& getData(subtype* deliberatelyNullPtr)
			{
			return static_cast<
				::CPPML::TaggedUnion<cppml_type, common_data_type, subtype>*
				>(mPointedTo)->data;
			}
		template<class subtype>
		const subtype& getData(subtype* deliberatelyNullPtr) const
			{
			return static_cast<
				const ::CPPML::TaggedUnion<cppml_type, common_data_type, subtype>*
				>(mPointedTo)->data;
			}

		template<class in_subtype, class in_common_type>
		static self_type create(typename cppml_type::tag_type tag, in_common_type&& inData, in_subtype&& inSubtype)
			{
			typedef typename remove_reference<in_subtype>::type real_subtype;

			return self_type(
				new TaggedUnion<cppml_type, common_data_type, real_subtype, default_t>(
					tag,
					::CPPML::forward<in_common_type>(inData),
					::CPPML::forward<in_subtype>(inSubtype)
					)
				);
			}
		void	incrementRefcount() const
			{
			mPointedTo->incrementRefcount();
			}
		bool	decrementRefcount() const
			{
			if (mPointedTo)
				return mPointedTo->decrementRefcount();
			return false;
			}

		unsigned long getRefcount() const
			{
			if (mPointedTo)
				return mPointedTo->getRefcount();

			return 0;
			}

		void	swap(self_type& other)
			{
			tagged_union_base_type* temp = other.mPointedTo;
			other.mPointedTo = mPointedTo;
			mPointedTo = temp;
			}

};

template<class T, class default_t>
class Validator {
public:
		void operator()(T& inElement) const
			{
			}
};

template<class T>
void validate(T& inElement)
	{
	Validator<T, void>()(inElement);
	}


class MatchError {
};

template<class tagged_union_type, class default_t>
class MatchErrorFactory {
public:
		typedef MatchError result_type;

		static MatchError matchError(const tagged_union_type& in)
			{
			return MatchError();
			}
};

template<class T>
typename MatchErrorFactory<T, void>::result_type
matchError(const T& in)
	{
	return MatchErrorFactory<T, void>::matchError(in);
	}


class Void {};
class BadUnionAccess {};

template<class tagged_union_type, class default_t>
class ThrowBadUnionAccess {
public:
		static void throwBadUnionAccess(const tagged_union_type& in) { throw BadUnionAccess(); }
};

template<class T> void throwBadUnionAccess(const T& in) { ThrowBadUnionAccess<T, void>::throwBadUnionAccess(in); }

template<class T>
void destroyInPlace(T* t)
		{
		t->~T();
		}

template<class TLeft, class TRight>
class Chain {
public:
		typedef TLeft left_type;
		typedef TRight right_type;
};

template<class tuple_type_in, class member_type_in, class accessor_in, const int member_index_in>
class TupleMember {
public:
		typedef tuple_type_in tuple_type;
		typedef member_type_in member_type;
		typedef accessor_in accessor;
		static const int member_index(void)
			{
			return member_index_in;
			}
};

template<class alternative_type_in, class member_type_in, class accessor_in, const int member_index_in>
class AlternativeCommonMember {
public:
		typedef alternative_type_in alternative_type;
		typedef member_type_in member_type;
		typedef accessor_in accessor;
		static const int member_index(void) { return member_index_in; }
};

template<class alternative_type_in, class data_type_in, class accessor_in>
class Alternative {
public:
		typedef alternative_type_in alternative_type;
		typedef data_type_in data_type;
		typedef accessor_in accessor;
};

template<class T>
class Refholder {
public:
		Refholder(const T& in) : m(in)
			{
			}
		const T& m;
};
template<class T>
class Valueholder {
public:
		Valueholder(const T& in) : m(in)
			{
			}
		T 	m;
};

template<class T>
Refholder<T>	grabMatchValue(const T& in)
	{
	return Refholder<T>(in);
	}
template<class T>
Valueholder<T> grabMatchValue(T&& in)
	{
	return Valueholder<T>(in);
	}


template<class T>
class CommonDataReplacer1 {
public:
	CommonDataReplacer1(const typename T::member_0_type& in, T& inToInitialize) :
			m(in),
			toInitialize(inToInitialize)
		{
		}

	template<class inner_tag_type>
	void operator()(const inner_tag_type& tag) const
		{
		toInitialize = T(m, tag);
		}
private:
	typename T::member_0_type m;
	T& toInitialize;
};

template<class T>
T replaceCommonData(const T& in, const typename T::member_0_type& s)
	{
	T toInitialize;
	in.visit(CommonDataReplacer1<T>(s, toInitialize));
	return toInitialize;
	}


}



