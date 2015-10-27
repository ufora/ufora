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

/**********
PolymorphicSharedPtr

These classes essentially emulate boost::shared_ptr, but they look different to
the boost::python infrastructure and so don't trigger some of the problematic conversions
that seem to interact badly with enable_shared_from_this.

They also allow us to expose an inheritance hierarchy in the pointers themselves.
This is primarily to allow boost to see the inheritance structure so that a

	PolymorphicSharedPtr<Base>

and a

	PolymorphicSharedPtr<Derived, PolymorphicSharedPtr<Base> >

will share the subclass arrangement.

Clients must descend the root type for PolymorphicSharedPtrBase<T>, e.g.

	class MyClass : public PolymorphicSharedPtrBase<MyClass> {
		...
	};

for the framework to be successful.
***********/

#include <boost/shared_ptr.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <utility>
#include "lassert.hpp"

template<class T>
class PolymorphicSharedPtrRoot;

template<class T>
class PolymorphicSharedWeakPtrRoot;

template<class T, class base_type = PolymorphicSharedPtrRoot<T> >
class PolymorphicSharedPtr;

template<class T, class base_type = PolymorphicSharedWeakPtrRoot<T> >
class PolymorphicSharedWeakPtr;


//all classes that want to use PolymorphicSharedPtr must descend from this class
template<class T>
class PolymorphicSharedPtrBase : public boost::enable_shared_from_this<T> {
		typedef T derived_type;

		friend class PolymorphicSharedPtrRoot<T>;
		friend class PolymorphicSharedPtr<T>;

		typedef T must_descend_from_PolymorphicSharedPtrBase;

public:
		PolymorphicSharedPtrBase() : mBaseIsInitialized(false)
			{
			}

		virtual ~PolymorphicSharedPtrBase()
			{
			}

		PolymorphicSharedPtr<T> polymorphicSharedPtrFromThis();

		PolymorphicSharedWeakPtr<T> polymorphicSharedWeakPtrFromThis();

protected:
		//override by children to initialize once 'polymorphicSharedPtrFromThis'
		//has been initialized
		virtual void polymorphicSharedPtrBaseInitialized()
			{
			}

		void polymorphicSharedPtrBaseInitialized_()
			{
			lassert(!mBaseIsInitialized);
			mBaseIsInitialized = true;

			polymorphicSharedPtrBaseInitialized();
			}
private:
		//make sure nobody can actually get to the shared_from_this by accident
		boost::shared_ptr<T> shared_from_this(void);

		bool mBaseIsInitialized;
};

//terminator in the shared-ptr chain
template<class T>
class PolymorphicSharedPtrRoot {
public:
		typedef PolymorphicSharedPtrBase<T> pointed_to_type;
		typedef PolymorphicSharedWeakPtrRoot<T> weak_ptr_type;

		~PolymorphicSharedPtrRoot()
			{
			}
protected:
		typedef T root_type;

		PolymorphicSharedPtrRoot()
			{
			}

		PolymorphicSharedPtrRoot(T* in) : mPtr(in)
			{
			typedef typename T::must_descend_from_PolymorphicSharedPtrBase
				check_T_descends_from_PolymorphicSharedPtrBase;

			in->polymorphicSharedPtrBaseInitialized_();
			}

		PolymorphicSharedPtrRoot(const boost::shared_ptr<T>& in) : mPtr(in)
			{
			}

		boost::shared_ptr<T> mPtr;

		friend class PolymorphicSharedWeakPtrRoot<T>;
		friend class PolymorphicSharedWeakPtr<T>;

		void callInitializer()
			{
			if (mPtr)
				mPtr->polymorphicSharedPtrBaseInitialized_();
			}
};

template<class T, class base_type_>
class PolymorphicSharedPtr : public base_type_ {
protected:
		friend class PolymorphicSharedWeakPtr<T, typename base_type_::weak_ptr_type>;
		friend class PolymorphicSharedPtrBase<T>;

		template<class T2, class base_type_2>
		friend class PolymorphicSharedPtr;

		PolymorphicSharedPtr(
					const boost::shared_ptr<typename base_type_::root_type>& in
					) : base_type_(in)
			{
			}
public:
		typedef T pointed_to_type;
		typedef base_type_ base_type;

		typedef PolymorphicSharedWeakPtr<T, typename base_type_::weak_ptr_type> weak_ptr_type;

		PolymorphicSharedPtr()
			{
			}
		explicit PolymorphicSharedPtr(T* in) :
						base_type_(in)
			{
			}
		static PolymorphicSharedPtr* Constructor0()
			{
			return new PolymorphicSharedPtr(new T());
			}
		template<class A1>
		static PolymorphicSharedPtr* Constructor1(const A1& inA1)
			{
			return new PolymorphicSharedPtr(new T(inA1));
			}

		template<class A1, class A2>
		static PolymorphicSharedPtr* Constructor2(const A1& inA1, const A2& inA2)
			{
			return new PolymorphicSharedPtr(new T(inA1, inA2));
			}

		template<class subtype>
		subtype dynamic_pointer_cast()
			{
			if (!this->mPtr)
				return subtype();

			typedef typename subtype::pointed_to_type sub_pointed_to_type;

			boost::shared_ptr<sub_pointed_to_type> sub =
				boost::dynamic_pointer_cast<sub_pointed_to_type>(this->mPtr);

			return subtype(sub);
			}

		void reset(T* in)
			{
			this->mPtr.reset(in);
			this->callInitializer();
			}
		void reset()
			{
			this->mPtr.reset();
			}
		T* get(void) const
			{
			lassert(this->mPtr);
			return static_cast<T*>(this->mPtr.get());
			}
		T& operator*() const
			{
			lassert(this->mPtr);
			return *get();
			}
		T* operator->() const
			{
			lassert(this->mPtr);
			return get();
			}
		operator bool() const
			{
			return bool(this->mPtr);
			}
		bool operator < (const PolymorphicSharedPtr& other) const
			{
			return this->mPtr < other.mPtr;
			}
		bool operator > (const PolymorphicSharedPtr& other) const
			{
			return this->mPtr > other.mPtr;
			}
		bool operator <= (const PolymorphicSharedPtr& other) const
			{
			return this->mPtr <= other.mPtr;
			}
		bool operator >= (const PolymorphicSharedPtr& other) const
			{
			return this->mPtr >= other.mPtr;
			}
		bool operator ==(const PolymorphicSharedPtr& other) const
			{
			return this->mPtr == other.mPtr;
			}
		bool operator != (const PolymorphicSharedPtr& other) const
			{
			return this->mPtr != other.mPtr;
			}
};

namespace std {
	template<class T, class base_type>
	class hash<PolymorphicSharedPtr<T, base_type>>
	{
	public:
		size_t operator() (const PolymorphicSharedPtr<T, base_type> &p) const
		{
		std::hash<T*> hasher;
		return hasher(p.get());
		}
	};
}


//terminator in the shared-ptr chain
template<class T>
class PolymorphicSharedWeakPtrRoot {
public:
		typedef T pointed_to_type;
		typedef PolymorphicSharedPtrRoot<T> strong_ptr_type;
protected:
		typedef T root_type;

		PolymorphicSharedWeakPtrRoot()
			{
			}
		PolymorphicSharedWeakPtrRoot(const PolymorphicSharedPtrRoot<T>& in) : mPtr(in.mPtr)
			{
			}

		boost::weak_ptr<T> mPtr;
};

template<class T, class base_type_>
class PolymorphicSharedWeakPtr : public base_type_ {
protected:
		explicit PolymorphicSharedWeakPtr(const boost::shared_ptr<T>& in) :
						base_type_(boost::dynamic_pointer_cast<typename base_type_::pointed_to_type>(in))
			{
			}
public:
		typedef T pointed_to_type;
		typedef base_type_ base_type;
		typedef PolymorphicSharedPtr<T, typename base_type_::strong_ptr_type> strong_ptr_type;
		typedef typename base_type_::root_type root_type;

		PolymorphicSharedWeakPtr()
			{
			}

		PolymorphicSharedWeakPtr(const strong_ptr_type& in) : base_type_(in)
			{
			}

		strong_ptr_type lock(void) const
			{
			boost::shared_ptr<root_type> p = this->mPtr.lock();

			if (!p)
				return strong_ptr_type();

			return strong_ptr_type(p);
			}
		bool expired(void) const
			{
			return this->mPtr.expired();
			}
		bool operator < (const PolymorphicSharedWeakPtr& other) const
			{
			return this->mPtr < other.mPtr;
			}
};

template<class T>
PolymorphicSharedPtr<T> PolymorphicSharedPtrBase<T>::polymorphicSharedPtrFromThis()
	{
	return PolymorphicSharedPtr<T>(
		static_cast<boost::enable_shared_from_this<T>* >(this)->shared_from_this()
		);
	}

template<class T>
PolymorphicSharedWeakPtr<T> PolymorphicSharedPtrBase<T>::polymorphicSharedWeakPtrFromThis()
	{
	return PolymorphicSharedWeakPtr<T>(polymorphicSharedPtrFromThis());
	}






