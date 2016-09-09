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
#include "IndexedMutex.hppml"
#include "../UnitTest.hpp"
#include "../Clock.hpp"
#include <mutex>
#include <string>

using namespace std;

BOOST_AUTO_TEST_CASE( test_Indexed_Mutex )
{
    IndexedMutex<string, boost::mutex> stringMutex;

    //verify that we can hold two distinct mutexes
    IndexedMutex<string, boost::mutex>::scoped_lock lock1(stringMutex, "m1");

    BOOST_CHECK(lock1.owns_lock());
    lock1.unlock();

    IndexedMutex<string, boost::mutex>::scoped_lock lock2(stringMutex, "m2");

    lock1.try_lock();

    //verify that we can lock both at the same time
    BOOST_CHECK(lock1.owns_lock() && lock2.owns_lock());

    lock1.unlock();
    lock2.unlock();

	IndexedMutex<string, boost::mutex>::scoped_lock lock3(stringMutex, "m1");
	lock1.try_lock();

	BOOST_CHECK(!lock1.owns_lock());

}

