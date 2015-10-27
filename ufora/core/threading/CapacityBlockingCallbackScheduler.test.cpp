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
#include "CapacityBlockingCallbackScheduler.hpp"
#include "SimpleCallbackSchedulerFactory.hppml"
#include "../Clock.hpp"
#include "../Logging.hpp"
#include "Queue.hpp"
#include <boost/bind.hpp>
#include "../UnitTest.hpp"
#include <vector>

namespace {

void scheduleSomeThings(
			CapacityBlockingCallbackScheduler* blockingScheduler, 
			std::vector<boost::function0<void> >* thingsToSchedule,
			boost::function0<void> somethingWasScheduled
			)
	{
	for (long k = 0; k < thingsToSchedule->size(); k++)
		{
		blockingScheduler->scheduleButBlockIfCapacityIsExceeded((*thingsToSchedule)[k], 1);
		somethingWasScheduled();
		}
	}

void doSomething(Queue<long>* toReadFromFirst, Queue<long>* toWriteToWhenDone)
	{
	long value = toReadFromFirst->get();

	toWriteToWhenDone->write(value);
	}

void waitForQueueToHaveExactlyNItems(const Queue<long>& queue, long count, bool& outFailed, double timeout = 1.0)
	{
	double t0 = curClock();

	while (queue.size() < count && curClock() - t0 < timeout)
		sleepSeconds(.00001);

	sleepSeconds(.001);

	if (queue.size() != count)
		{
		LOG_ERROR << "timed out: " << queue.size() << " != " << count;

		outFailed = true;
		}
	}

}

BOOST_AUTO_TEST_CASE( test_capacityBlockingCallbackScheduler )
	{
	long capacity = 10;

	PolymorphicSharedPtr<CallbackSchedulerFactory> factory(
			new SimpleCallbackSchedulerFactory()
			);

	for (long pass = 0; pass < 10; pass++)
		{
		PolymorphicSharedPtr<CallbackScheduler> scheduler(factory->createScheduler("", 1));

		CapacityBlockingCallbackScheduler blockingScheduler(scheduler, capacity);

		bool failed = false;

		LOG_INFO << pass;

		Queue<long> toWriteTo;
		Queue<long> thingsScheduled;
		Queue<long> toReadFrom;

		std::vector<boost::function0<void> > thingsToDo1;
		std::vector<boost::function0<void> > thingsToDo2;

		for (long k = 0; k < capacity; k++)
			thingsToDo1.push_back(
				boost::bind(doSomething, &toReadFrom, &toWriteTo)
				);
		for (long k = 0; k < capacity; k++)
			thingsToDo2.push_back(
				boost::bind(doSomething, &toReadFrom, &toWriteTo)
				);

		boost::function0<void> writeToScheduledQueue = 
				boost::bind(
					&Queue<long>::write,
					&thingsScheduled,
					(long)0
					);


		boost::thread t1(
			boost::bind(
				scheduleSomeThings, 
				&blockingScheduler, 
				&thingsToDo1, 
				writeToScheduledQueue
				)
			);

		boost::thread t2(
			boost::bind(
				scheduleSomeThings, 
				&blockingScheduler, 
				&thingsToDo2, 
				writeToScheduledQueue
				)
			);

		//we should now see exactly ten things get written into 'thingsScheduled'
		waitForQueueToHaveExactlyNItems(thingsScheduled, capacity, failed);

		for (long k = 0; k < capacity * 2; k++)
			{
			waitForQueueToHaveExactlyNItems(
				thingsScheduled, 
				std::min(capacity + k, capacity * 2), 
				failed
				);

			toReadFrom.write(k);

			waitForQueueToHaveExactlyNItems(
				thingsScheduled, 
				std::min(capacity + k + 1, capacity * 2), 
				failed
				);

			waitForQueueToHaveExactlyNItems(toWriteTo, k + 1, failed);
			}

		t1.join();
		t2.join();

		lassert(!failed);
		}
	}

