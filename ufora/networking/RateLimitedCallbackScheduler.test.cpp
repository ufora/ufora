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
#include "RateLimitedCallbackScheduler.hppml"
#include "../core/threading/SimpleCallbackSchedulerFactory.hppml"
#include "../core/threading/Queue.hpp"
#include "../core/UnitTest.hpp"
#include "../core/Clock.hpp"

BOOST_AUTO_TEST_SUITE( test_RateLimitedCallbackScheduler )

BOOST_AUTO_TEST_CASE( test_single_threaded )
	{
	PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > limited(
		new RateLimitedCallbackScheduler<int>(
			SimpleCallbackSchedulerFactory::singletonSchedulerForTesting(),
			1.0
			)
		);

	Queue<long> queue;

	long anInteger = 12345;

	double t0 = curClock();

	limited->schedule(
		0.01,
		0,
		boost::function0<void>([&](){ queue.write(anInteger); })
		);

	long output;
	BOOST_CHECK(queue.getTimeout(output, 1.0));
	BOOST_CHECK(output == anInteger);
	BOOST_CHECK(curClock() - t0 > 0.01);
	}

BOOST_AUTO_TEST_CASE( test_sequence )
	{
	PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > limited(
		new RateLimitedCallbackScheduler<int>(
			SimpleCallbackSchedulerFactory::singletonSchedulerForTesting(),
			1.0
			)
		);

	Queue<long> queue;

	long anInteger = 12345;

	double t0 = curClock();

	limited->schedule(0.01, 0, boost::function0<void>([&](){ queue.write(anInteger); }));
	limited->schedule(0.01, 0, boost::function0<void>([&](){ queue.write(anInteger+1); }));
	limited->schedule(0.01, 0, boost::function0<void>([&](){ queue.write(anInteger+2); }));
	limited->schedule(0.01, 0, boost::function0<void>([&](){ queue.write(anInteger+3); }));

	long output;
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 1);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 2);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 3);
	BOOST_CHECK(curClock() - t0 > 0.04);
	}

BOOST_AUTO_TEST_CASE( test_simultaneous )
	{
	PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > limited(
		new RateLimitedCallbackScheduler<int>(
			SimpleCallbackSchedulerFactory::singletonSchedulerForTesting(),
			1.0
			)
		);

	Queue<long> queue;

	long anInteger = 12345;

	double t0 = curClock();

	limited->schedule(0.1, 0, boost::function0<void>([&](){ queue.write(anInteger); }));
	limited->schedule(0.1, 1, boost::function0<void>([&](){ queue.write(anInteger+1); }));
	limited->schedule(0.1, 2, boost::function0<void>([&](){ queue.write(anInteger+2); }));
	limited->schedule(0.1, 3, boost::function0<void>([&](){ queue.write(anInteger+3); }));

	long output;
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger);
	BOOST_CHECK(curClock() - t0 > 0.3);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 1);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 2);
	BOOST_CHECK(queue.getTimeout(output, 1.0) && output == anInteger + 3);
	BOOST_CHECK(curClock() - t0 < 0.5);
	}


BOOST_AUTO_TEST_SUITE_END( )


