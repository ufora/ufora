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
#include "Channel.hpp"

#include "../core/serialization/Serialization.hpp"
#include "../core/UnitTest.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "InMemoryChannel.hpp"
#include "SerializedChannel.hpp"
#include "../distributed/SharedState/Message.hppml"

using namespace SharedState;

BOOST_AUTO_TEST_CASE( test_SerializedChannelTest )
	{
	PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());
	auto pRaw = InMemoryChannel<std::string, std::string>::createChannelPair(scheduler);

	pair<channel_ptr_type, string_channel_ptr_type> channelPair(
		makeQueuelikeChannel(
			scheduler,
			new serialized_channel_type(scheduler, pRaw.first)
			),
		makeQueuelikeChannel(
			scheduler,
			pRaw.second
			)
		);

	auto messageChannel = channelPair.first;
	auto stringChannel = channelPair.second;

	auto messageOut = MessageOut::MinimumIdResponse(42);
	messageChannel->write(messageOut);

	std::string serializedMessage = stringChannel->get();
	BOOST_CHECK(!serializedMessage.empty());

	auto deserializedMessage = deserialize<MessageOut>(serializedMessage);
	BOOST_CHECK_EQUAL(
		messageOut.getMinimumIdResponse().id(), 
		deserializedMessage.getMinimumIdResponse().id()
		);

	auto messageIn = MessageIn::MinimumId(11, 42);
	stringChannel->write(serialize<MessageIn>(messageIn));

	auto receivedMessage = messageChannel->get();
	BOOST_CHECK_EQUAL(
		messageIn.getMinimumId().id(),
		receivedMessage.getMinimumId().id()
		);
	BOOST_CHECK_EQUAL(
		messageIn.getMinimumId().maxId(),
		receivedMessage.getMinimumId().maxId()
		);
	}

