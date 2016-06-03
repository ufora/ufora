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
#pragma once

#include "../core/PolymorphicSharedPtr.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "../core/math/Nullable.hpp"
#include "../core/Clock.hpp"
#include "../core/serialization/Serialization.hpp"
#include "../core/serialization/SerializedObjectStream.hppml"
#include "../core/threading/BSAThread.hpp"
#include <boost/bind.hpp>

class ChannelDisconnected : public std::logic_error {
public:
		ChannelDisconnected() : std::logic_error("channel disconnected")
			{
			}
};

/*****************
Channel

Allows you to read and write messages. Throws "ChannelDisconnected" when the channel is known
to be disconnected. Channels are required to block (holding onto received messages) until
their handlers are set.

******************/


template<class TOut, class TIn>
class Channel : public PolymorphicSharedPtrBase<Channel<TOut, TIn> > {
public:
	typedef PolymorphicSharedPtr<Channel<TOut, TIn> > pointer_type;

	typedef PolymorphicSharedWeakPtr<Channel<TOut, TIn> > weak_ptr_type;

	typedef Channel<TOut, TIn> self_type;
	typedef Channel<TIn, TOut> reverse_channel_type;

	typedef TOut message_out_type;
	typedef TIn  message_in_type;

	typedef boost::function1<void, message_in_type> on_message_handler_type;
	typedef boost::function0<void> on_disconnected_handler_type;

	virtual ~Channel() {}

	virtual void write(const message_out_type& in) = 0;

	virtual void disconnect() = 0;

	virtual void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler) = 0;

	virtual PolymorphicSharedPtr<CallbackScheduler> getScheduler() = 0;

	virtual void setHandlers(
		on_message_handler_type inOnMessage,
		on_disconnected_handler_type inOnDisconnected
		) = 0;

	virtual std::string channelType() = 0;
};


