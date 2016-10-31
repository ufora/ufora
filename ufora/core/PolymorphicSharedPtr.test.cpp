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
#include "PolymorphicSharedPtr.hpp"
#include "UnitTest.hpp"

namespace {

unsigned long a_count = 0, b_count = 0;

class A : public PolymorphicSharedPtrBase<A> {
public:
		A(int i) : m(i)
			{
			a_count++;
			}
		virtual ~A()
			{
			a_count--;
			}

		int m;
};


class B : public A {
public:
		B(int i) : A(i), m2(i+1)
			{
			b_count++;
			}
		virtual ~B()
			{
			b_count--;
			}

		int m2;
};

class InitializerTester : public PolymorphicSharedPtrBase<InitializerTester> {
public:
	InitializerTester() :
			mInitCount(0)
		{

		}

	void polymorphicSharedPtrBaseInitialized()
		{
		mInitCount++;

		polymorphicSharedPtrFromThis();
		}

	long mInitCount;
};

};

BOOST_AUTO_TEST_SUITE( test_PolymorphicSharedPtr )

	typedef PolymorphicSharedPtr<A> a_ptr_type;
	typedef PolymorphicSharedPtr<B, PolymorphicSharedPtr<A> > b_ptr_type;

	PolymorphicSharedPtr<A> 									a, a2;
	PolymorphicSharedWeakPtr<A> 								aWeak, aWeak2;
	PolymorphicSharedPtr<B, PolymorphicSharedPtr<A> >			b, b2;
	PolymorphicSharedWeakPtr<B, PolymorphicSharedWeakPtr<A> >	bWeak, bWeak2;

BOOST_AUTO_TEST_CASE( test_refcounting )
	{
	a.reset(new A(1));

	//check boolean
	BOOST_CHECK(a);
	BOOST_CHECK(!b);

	BOOST_CHECK_EQUAL(a_count, 1);
	a.reset();

	//verify this destroyed the 'a'
	BOOST_CHECK_EQUAL(a_count, 0);
	}

BOOST_AUTO_TEST_CASE( test_holds_subclass )
	{
	//verify that it's holding the B correctly
	a.reset(new B(1));
	BOOST_CHECK_EQUAL(a_count, 1);
	BOOST_CHECK_EQUAL(b_count, 1);

	//verify that destroying 'a' calls the right destructor
	a.reset();
	BOOST_CHECK_EQUAL(a_count, 0);
	BOOST_CHECK_EQUAL(b_count, 0);
	}

BOOST_AUTO_TEST_CASE( test_assignment_of_subclass_to_baseclass )
	{
	//put something in 'b'
	b.reset(new B(1));

	BOOST_CHECK_EQUAL(a_count, 1);
	BOOST_CHECK_EQUAL(b_count, 1);

	//make sure we can access the right members of the subclass
	BOOST_CHECK_EQUAL(b->m, 1);
	BOOST_CHECK_EQUAL(b->m2, 2);

	//verify we can assign b to a because b is a subclass of a
	a = b;

	//they're the same object
	BOOST_CHECK_EQUAL(&a->m, &b->m);

	//reset B and verify we still have a reference
	b.reset();

	BOOST_CHECK_EQUAL(a_count, 1);
	BOOST_CHECK_EQUAL(b_count, 1);

	a.reset();

	BOOST_CHECK_EQUAL(a_count, 0);
	BOOST_CHECK_EQUAL(b_count, 0);
	}

BOOST_AUTO_TEST_CASE( test_weak_ptr )
	{
	a.reset(new A(1));

	aWeak = a;

	BOOST_CHECK_EQUAL(a_count, 1);

	BOOST_CHECK(aWeak.lock());

	BOOST_CHECK_EQUAL(a_count, 1);

	BOOST_CHECK(aWeak.lock());

	BOOST_CHECK(&*aWeak.lock() == &*a);

	a.reset();
	BOOST_CHECK(!aWeak.lock());
	}

BOOST_AUTO_TEST_CASE( test_weakptr_base )
	{
	b.reset(new B(1));

	BOOST_CHECK(b == b->polymorphicSharedPtrFromThis());

	bWeak = b;

	BOOST_CHECK(bWeak.lock());
	BOOST_CHECK(&*bWeak.lock() == &*b);

	aWeak = bWeak;
	a = aWeak.lock();

	b.reset();

	BOOST_CHECK(bWeak.lock());
	BOOST_CHECK_EQUAL(b_count, 1);
	BOOST_CHECK_EQUAL(a_count, 1);

	a.reset();
	BOOST_CHECK(bWeak.expired());

	BOOST_CHECK_EQUAL(b_count, 0);
	BOOST_CHECK_EQUAL(a_count, 0);
	}

BOOST_AUTO_TEST_CASE( test_polymophicSharedFromThis )
	{
	a.reset(new A(1));

	BOOST_CHECK_EQUAL(a_count, 1);

	a2 = a->polymorphicSharedPtrFromThis();

	BOOST_CHECK(a == a2);

	a.reset();

	BOOST_CHECK_EQUAL(a_count, 1);

	a2.reset();
	BOOST_CHECK_EQUAL(a_count, 0);
	}

BOOST_AUTO_TEST_CASE( test_equality_operators )
	{
	a.reset(new A(1));
	a2.reset(new A(2));

	BOOST_CHECK(a != a2);
	BOOST_CHECK(a == a);
	BOOST_CHECK(a2 == a2);

	BOOST_CHECK(a < a2 || a2 < a);
	}

BOOST_AUTO_TEST_CASE( test_dynamic_cast )
	{
	a.reset(new A(1));
	a2.reset(new B(1));

	BOOST_CHECK(a.dynamic_pointer_cast<a_ptr_type>());
	BOOST_CHECK(!a.dynamic_pointer_cast<b_ptr_type>());

	BOOST_CHECK(a2.dynamic_pointer_cast<a_ptr_type>());
	BOOST_CHECK(a2.dynamic_pointer_cast<b_ptr_type>());
	}

BOOST_AUTO_TEST_CASE( test_initializer_counter )
	{
	PolymorphicSharedPtr<InitializerTester> p1(new InitializerTester());

	BOOST_CHECK(p1->mInitCount == 1);

	//verify that the copy operation doesn't call it again
	PolymorphicSharedPtr<InitializerTester> p2;
	p2 = p1;

	BOOST_CHECK(p2->mInitCount == 1);
	}

BOOST_AUTO_TEST_SUITE_END( )

