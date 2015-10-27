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
#include "ReturnValue.hpp"

#include "../../core/UnitTest.hpp"

using namespace Fora;

BOOST_AUTO_TEST_CASE( test_ReturnValue )
	{
	Fora::ReturnValue<long, double, std::string> returnValue;

	returnValue = slot0(1);
	BOOST_CHECK(returnValue.getIndex() == 0);
	BOOST_CHECK(returnValue.get0() == 1);
	BOOST_CHECK_THROW(returnValue.get1(), std::logic_error);

	returnValue = slot1(1);
	BOOST_CHECK(returnValue.getIndex() == 1);
	BOOST_CHECK(returnValue.get1() == 1.0);
	
	returnValue = slot2(std::string("hello"));
	BOOST_CHECK(returnValue.getIndex() == 2);
	BOOST_CHECK(returnValue.get2() == "hello");

	Fora::ReturnValue<long, double, std::string> returnValue2;
	returnValue2 = returnValue;

	BOOST_CHECK(returnValue2.getIndex() == 2);

	Fora::ReturnValue<long, double, std::string> returnValue3;
	returnValue3 = slot1(1);

	returnValue2 = returnValue3;
	BOOST_CHECK(returnValue2.getIndex() == 1);

	Fora::ReturnValue<long, double, std::string> returnValue4(returnValue3);
	BOOST_CHECK(returnValue3.getIndex() == returnValue4.getIndex());
	}

namespace {

class SomethingLarge {
public:
	uword_t a,b,c,d,e,f,g;
};
class SomethingSmall {
public:
	bool b;
};

}


BOOST_AUTO_TEST_CASE( test_ReturnValueSize )
	{
	BOOST_CHECK(sizeof(Fora::ReturnValue<SomethingLarge>) 
		== sizeof(SomethingLarge) + sizeof(uword_t)
		);
	BOOST_CHECK(sizeof(Fora::ReturnValue<SomethingSmall, SomethingLarge>) 
		== sizeof(SomethingLarge) + sizeof(uword_t)
		);
	BOOST_CHECK(sizeof(Fora::ReturnValue<SomethingLarge, SomethingSmall>) 
		== sizeof(SomethingLarge) + sizeof(uword_t)
		);
	BOOST_CHECK(sizeof(Fora::ReturnValue<SomethingSmall, SomethingSmall, SomethingSmall, SomethingLarge>) 
		== sizeof(SomethingLarge) + sizeof(uword_t)
		);
	}

