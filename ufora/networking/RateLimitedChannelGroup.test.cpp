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
#include "RateLimitedChannelGroup.hpp"

#include "../core/serialization/Serialization.hpp"
#include "../core/UnitTest.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "InMemoryChannel.hpp"
#include "QueuelikeChannel.hppml"

BOOST_AUTO_TEST_CASE( test_rate_limited_channel_group )
	{
	typedef QueuelikeChannel<std::string, std::string>::pointer_type queuelike_channel;

	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());

	PolymorphicSharedPtr<RateLimitedChannelGroup<std::string, std::string> > rateLimitedGroup(
		new RateLimitedChannelGroup<std::string, std::string>(
			scheduler,
			boost::function1<double, std::string>([](std::string s) { return (double)s.size(); }),
			boost::function1<double, std::string>([](std::string s) { return (double)s.size(); }),
			1000
			)
		);

	auto makeStringChannels = [&]() {
		auto rawChannels =
			InMemoryChannel<std::string, std::string>::createChannelPair(scheduler);

		return pair<queuelike_channel, queuelike_channel>(
			makeQueuelikeChannel(
				scheduler,
				rateLimitedGroup->wrap(rawChannels.first)
				),
			makeQueuelikeChannel(
				scheduler,
				rawChannels.second
				)
			);
		};

	pair<queuelike_channel, queuelike_channel> stringChannels1 = makeStringChannels();
	pair<queuelike_channel, queuelike_channel> stringChannels2 = makeStringChannels();

	//test that we are rate limited on one channel
		{
		double t0 = curClock();

		for (long k = 0; k < 1000; k++)
			stringChannels1.first->write("a");

		for (long k = 0; k < 1000; k++)
			BOOST_CHECK(stringChannels1.second->getOrTimeoutAndAssert(1.0) == "a");

		BOOST_CHECK(curClock() - t0 > .5);
		BOOST_CHECK(curClock() - t0 < 1.5);
		}

	//test that we're rate limited on both channels and that messages arrive equally
		{
		double t0 = curClock();

		for (long k = 0; k < 1000; k++)
			{
			stringChannels1.first->write("a");
			stringChannels2.first->write("b");
			}

		for (long k = 0; k < 1000; k++)
			{
			BOOST_CHECK(stringChannels1.second->getOrTimeoutAndAssert(1.0) == "a");
			BOOST_CHECK(stringChannels2.second->getOrTimeoutAndAssert(1.0) == "b");
			}

		BOOST_CHECK(curClock() - t0 > 1.5);
		BOOST_CHECK(curClock() - t0 < 2.5);
		}
	}

