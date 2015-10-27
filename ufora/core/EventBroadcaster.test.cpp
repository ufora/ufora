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
#include "EventBroadcaster.hpp"

#include "UnitTest.hpp"

namespace {

class TestClass : public PolymorphicSharedPtrBase<TestClass> {
public:
	TestClass() : mCounter(0)
		{
		}

	void increment(long count)
		{
		mCounter += count;
		sleepSeconds(.01);
		}

	void incrementTwice(long count)
		{
		mCounter += count * 2;
		sleepSeconds(.01);
		}

	int mCounter;
};

}

BOOST_AUTO_TEST_CASE( test_EventBroadcaster )
	{
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());
	EventBroadcaster<long> broadcaster(scheduler);

	PolymorphicSharedPtr<TestClass> testClass1(new TestClass());
	PolymorphicSharedPtr<TestClass> testClass2(new TestClass());

	broadcaster.subscribe(testClass1, &TestClass::increment);
	broadcaster.subscribe(testClass2, &TestClass::incrementTwice);

	broadcaster.broadcast(10);
	broadcaster.broadcast(20);

	scheduler->blockUntilPendingHaveExecuted();

	BOOST_CHECK_EQUAL(testClass1->mCounter, 30);
	BOOST_CHECK_EQUAL(testClass2->mCounter, 60);

	testClass2 = PolymorphicSharedPtr<TestClass>();

	broadcaster.broadcast(10);
	broadcaster.broadcast(20);

	scheduler->blockUntilPendingHaveExecuted();

	BOOST_CHECK_EQUAL(testClass1->mCounter, 60);
	}

