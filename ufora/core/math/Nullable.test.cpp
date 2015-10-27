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
#include "Nullable.hpp"
#include "../UnitTest.hpp"

BOOST_AUTO_TEST_CASE( test_core_math_Nullable_comparison_1 )
{
	Nullable<int> val_null;
	Nullable<int> val_1(1);
	Nullable<int> val_2(2);
	
	BOOST_CHECK(  (val_null == val_null));
	BOOST_CHECK( !(val_null != val_null));
	BOOST_CHECK(  (val_null <= val_null));
	BOOST_CHECK(  (val_null >= val_null));
	BOOST_CHECK( !(val_null <  val_null));
	BOOST_CHECK( !(val_null >  val_null));
	
	BOOST_CHECK( !(val_null == val_1));
	BOOST_CHECK(  (val_null != val_1));
	BOOST_CHECK(  (val_null <= val_1));
	BOOST_CHECK( !(val_null >= val_1));
	BOOST_CHECK(  (val_null <  val_1));
	BOOST_CHECK( !(val_null >  val_1));

	BOOST_CHECK(  (val_1 == val_1));
	BOOST_CHECK( !(val_1 != val_1));
	BOOST_CHECK(  (val_1 <= val_1));
	BOOST_CHECK(  (val_1 >= val_1));
	BOOST_CHECK( !(val_1 <  val_1));
	BOOST_CHECK( !(val_1 >  val_1));
	
	BOOST_CHECK( !(val_1 == val_2));
	BOOST_CHECK(  (val_1 != val_2));
	BOOST_CHECK(  (val_1 <= val_2));
	BOOST_CHECK( !(val_1 >= val_2));
	BOOST_CHECK(  (val_1 <  val_2));
	BOOST_CHECK( !(val_1 >  val_2));
}

BOOST_AUTO_TEST_CASE( test_core_math_Nullable_comparison_2 )
{
	Nullable<long> val;
	BOOST_CHECK(!val);
	val = 0;
	BOOST_CHECK(val);	
}
