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
#include "ArbitraryTypeMap.hpp"
#include "../UnitTest.hpp"

namespace {

template<class T>
class Type {
public:
	Type()
		{
		instanceCount++;
		}

	Type(const Type& in) :
			val(in.val)
		{
		instanceCount++;
		}

	~Type()
		{
		instanceCount--;
		}

	static long instanceCount;

	T val;
};

template<class T>
long Type<T>::instanceCount;

}

BOOST_AUTO_TEST_CASE( test_ArbitraryTypeMap_create )
	{
	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);

	ArbitraryTypeMap m;

	m.get<Type<int> >().val = 10;

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 1);

	m.erase<Type<int> >();

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);
	}

BOOST_AUTO_TEST_CASE( test_ArbitraryTypeMap_multiple )
	{
	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);

	ArbitraryTypeMap m1,m2;

	m1.get<Type<int> >().val = 10;
	m2.get<Type<int> >().val = 20;

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 2);
	}

BOOST_AUTO_TEST_CASE( test_ArbitraryTypeMap_copy )
	{
	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);

	ArbitraryTypeMap m1,m2;

	m1.get<Type<int> >().val = 10;

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 1);

	m2 = m1;

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 2);

	m1.get<Type<int> >().val = 20;

	BOOST_CHECK_EQUAL(m1.get<Type<int> >().val, 20);
	BOOST_CHECK_EQUAL(m2.get<Type<int> >().val, 10);
	}


BOOST_AUTO_TEST_CASE( test_ArbitraryTypeMap_clear )
	{
	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);

	ArbitraryTypeMap m1;

	m1.get<Type<int> >().val = 10;

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 1);

	m1.clear();

	BOOST_CHECK_EQUAL(Type<int>::instanceCount, 0);
	}

