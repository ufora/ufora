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
#include <initializer_list>
#include <queue>
#include <boost/function.hpp>

#include "OrderedMessage.hppml"

#include "../core/ScopedProfiler.hppml"
#include "../core/PolymorphicSharedPtr.hpp"
#include "../core/PolymorphicSharedPtrBinder.hpp"

template <class TOut, class TIn>
class MultiChannel : public Channel<TOut, TIn> {
public:
	typedef PolymorphicSharedPtr<
				MultiChannel<TOut, TIn>,
				typename Channel<TOut, TIn>::pointer_type
			> pointer_type;

	typedef PolymorphicSharedWeakPtr<
				MultiChannel<TOut, TIn>,
				typename Channel<TOut, TIn>::weak_ptr_type
			> weak_ptr_type;

	typedef Channel<OrderedMessage<TOut>, OrderedMessage<TIn>> ordered_channel_type;
	typedef typename ordered_channel_type::pointer_type ordered_channel_pointer_type;

	typedef uint32_t message_ordinal_type;

	typedef boost::function<size_t(TOut)> outgoing_channel_selector;

	MultiChannel(
			std::initializer_list<ordered_channel_pointer_type> channels,
			outgoing_channel_selector channelSelector,
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
			) :
		mChannels(channels.begin(), channels.end()),
		mOutgoingChannelSelector(channelSelector),
		mIsDisconnected(false),
		mLastOutboundMessageOrdinal(0),
		mMaxDispatchedMessageOrdinal(0),
		mCallbackScheduler(inCallbackScheduler)
		{
		}

	MultiChannel(
			std::vector<ordered_channel_pointer_type> channels,
			outgoing_channel_selector channelSelector,
			PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler
			) :
		mChannels(channels.begin(), channels.end()),
		mOutgoingChannelSelector(channelSelector),
		mIsDisconnected(false),
		mLastOutboundMessageOrdinal(0),
		mMaxDispatchedMessageOrdinal(0),
		mCallbackScheduler(inCallbackScheduler)
		{
		}

	~MultiChannel() {}
	
	virtual std::string channelType()
		{
		return "MultiChannel";
		}

	void write(const TOut& msg)
		{
		size_t channelIndex = mOutgoingChannelSelector(msg);
		lassert(channelIndex < mChannels.size());

		boost::mutex::scoped_lock lock(mMutex);
		uint32_t newOrdinal = ++mLastOutboundMessageOrdinal;
		mChannels[channelIndex]->write(OrderedMessage<TOut>(newOrdinal, msg));
		}

	void disconnect()
		{
			{
			boost::mutex::scoped_lock lock(mMutex);
			if (mIsDisconnected)
				return;

			mIsDisconnected = true;
			}

		for (auto it = mChannels.begin(); it != mChannels.end(); ++it)
			{
			(*it)->disconnect();
			}

		if (mOnDisconnected)
			mOnDisconnected();
		}

	void setHandlers(
			typename Channel<TOut, TIn>::on_message_handler_type inOnMessage,
			typename Channel<TOut, TIn>::on_disconnected_handler_type inOnDisconnected
			)
		{
		boost::mutex::scoped_lock lock(mMutex);
		mOnMessage = inOnMessage;
		mOnDisconnected = inOnDisconnected;

		for (size_t i = 0; i < mChannels.size(); i++)
			{
			mChannels[i]->setHandlers(
				ChannelCallbackHandler(
					weak_ptr_type(
						this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
						),
					i
					),
				ChannelCallbackHandler(
					weak_ptr_type(
						this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
						),
					i
					)
				);
			}
		}

private:
	class ChannelCallbackHandler {
	public:
		ChannelCallbackHandler(
				weak_ptr_type multiChannel,
				size_t channelIndex) :
			mMultiChannel(multiChannel),
			mChannelIndex(channelIndex)
			{
			}

		void operator() (typename ordered_channel_type::message_in_type message)
			{
			pointer_type p = mMultiChannel.lock();

			if (p)
				p->incomingMessageOnChannel(mChannelIndex, message);
			}

		void operator() ()
			{
			pointer_type p = mMultiChannel.lock();

			if (p)
				p->channelDisconnected(mChannelIndex);
			}

	private:
		weak_ptr_type mMultiChannel;
		size_t mChannelIndex;
	};


	void incomingMessageOnChannel(
			size_t channelIndex,
			typename ordered_channel_type::message_in_type message
			)
		{
		lassert(mOnMessage);

		message_ordinal_type ordinal = message.ordinal();

		LOG_DEBUG << "MultiChannel " << this << ". Incoming message with ordinal " << ordinal << " on channel " << channelIndex
					  << ". Max dispatched ordinal: " << mMaxDispatchedMessageOrdinal;

			{
			boost::mutex::scoped_lock lock(mMutex);
			
			Ufora::ScopedProfiler<std::string> unpackTokenProfiler("multiChannelIncomingMessage");
			
			if (shouldDelayMessage_(channelIndex, ordinal))
				{
				mDelayedMessages.push(make_tuple(ordinal, channelIndex, message.message()));
				return;
				}
			mMaxDispatchedMessageOrdinal = std::max(mMaxDispatchedMessageOrdinal, ordinal);
			scheduleMessageCallback(message.message());
			dispatchDelayedMessages(ordinal);
			}

		}

	void scheduleMessageCallback(TIn message)
		{
		mCallbackScheduler->scheduleImmediately(
			boost::bind(mOnMessage, message), 
			"MultiChannel::mOnMessage"
			);
		}

	bool shouldDelayMessage_(size_t channelIndex, message_ordinal_type ordinal)
		{
		if (ordinal <= mMaxDispatchedMessageOrdinal + 1)
			return false;  // we've already seen greater ordinals

		if (channelIndex == 0)
			return false; // don't delay message in the highest-priority channel

		LOG_DEBUG << "MultiChannel " << this << " delaying message on channel " << channelIndex
			<< ". current ordinal: " << ordinal
			<< ". max dispatched ordinal: " << mMaxDispatchedMessageOrdinal
			;

		return true;
		}

	void dispatchDelayedMessages(message_ordinal_type lastOrdinal)
		{
		while (shouldDispatchNextDelayedMessage(lastOrdinal))
			{
			const delayed_message_tuple& delayedMessage = mDelayedMessages.top();
			
			LOG_DEBUG << "MultiChannel " << this << " dispatching delayed message. Channel: " 
				<< std::get<1>(delayedMessage)
				<< ". Ordinal: " << std::get<0>(delayedMessage);

			message_ordinal_type delayedOrdinal = getOrdinal(delayedMessage);

			lastOrdinal = std::max(lastOrdinal, delayedOrdinal);
			
			mMaxDispatchedMessageOrdinal = std::max(mMaxDispatchedMessageOrdinal, delayedOrdinal);
			scheduleMessageCallback(getMessage(delayedMessage));
			mDelayedMessages.pop();
			}
		}

	bool shouldDispatchNextDelayedMessage(message_ordinal_type lastOrdinal)
		{
		return !mDelayedMessages.empty() &&
			   getOrdinal(mDelayedMessages.top()) <= lastOrdinal + 1;
		}

	void channelDisconnected(size_t channelIndex)
		{
		disconnect();
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		boost::mutex::scoped_lock lock(mMutex);

		mCallbackScheduler = inScheduler;
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		boost::mutex::scoped_lock lock(mMutex);

		return mCallbackScheduler;
		}

private:
	typedef std::tuple<
				message_ordinal_type,
				size_t,   // channel index
				typename Channel<TOut, TIn>::message_in_type
			> delayed_message_tuple;

	static message_ordinal_type getOrdinal(const delayed_message_tuple& delayedMessage)
		{
		return std::get<0>(delayedMessage);
		}

	static size_t getChannelIndex(const delayed_message_tuple& delayedMessage)
		{
		return std::get<1>(delayedMessage);
		}

	static typename Channel<TOut, TIn>::message_in_type getMessage(
			const delayed_message_tuple& delayedMessage
			)
		{
		return std::get<2>(delayedMessage);
		}

	typedef std::priority_queue<
				delayed_message_tuple,
				std::vector<delayed_message_tuple>,
				std::greater<delayed_message_tuple>
				> message_priority_queue;

	PolymorphicSharedPtr<CallbackScheduler>						mCallbackScheduler;
	std::vector<ordered_channel_pointer_type>					mChannels;
	typename Channel<TOut, TIn>::on_message_handler_type		mOnMessage;
	typename Channel<TOut, TIn>::on_disconnected_handler_type	mOnDisconnected;
	outgoing_channel_selector									mOutgoingChannelSelector;
	message_priority_queue										mDelayedMessages;
	bool 														mIsDisconnected;
	uint32_t 													mLastOutboundMessageOrdinal;
	uint32_t 													mMaxDispatchedMessageOrdinal;
	boost::mutex 												mMutex;
		
};


