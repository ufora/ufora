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
#include "QueuelikeChannel.hppml"

#include "../core/UnitTest.hpp"
#include "InMemoryChannel.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "../distributed/SharedState/Message.hppml"

namespace {

void doNothing(void)
	{

	}

}

BOOST_AUTO_TEST_CASE( test_QueuelikeChannel_BecomesNormalChannel )
	{
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());
	auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(scheduler);

	auto queuelikeChannel = makeQueuelikeChannel(scheduler, pRaw.first);

	pRaw.second->write("A");
	pRaw.second->write("B");
	pRaw.second->write("C");

	BOOST_CHECK_EQUAL(queuelikeChannel->get(), "A");

	std::vector<std::string> vec;

	queuelikeChannel->setHandlers(
		boost::bind(
			(void (std::vector<std::string>::*)(const std::string&))
				&std::vector<std::string>::push_back,
			&vec,
			boost::arg<1>()
			),
		&doNothing
		);

	scheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

	BOOST_CHECK_EQUAL(vec.size(), 2);
	BOOST_CHECK_EQUAL(vec[0], "B");
	BOOST_CHECK_EQUAL(vec[1], "C");

	pRaw.second->write("D");
	
	scheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

	BOOST_CHECK_EQUAL(vec.size(), 3);
	BOOST_CHECK_EQUAL(vec[2], "D");
	}

