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

#include "Channel.hpp"
#include "RateLimitedCallbackScheduler.hppml"

template<class TOut, class TIn>
class RateLimitedChannel : public Channel<TOut, TIn> {
public:
	typedef PolymorphicSharedPtr<RateLimitedChannel<TOut, TIn>, typename Channel<TOut, TIn>::pointer_type> pointer_type;

	typedef PolymorphicSharedWeakPtr<RateLimitedChannel<TOut, TIn>, typename Channel<TOut, TIn>::weak_ptr_type> weak_ptr_type;

	typedef TOut message_out_type;
	typedef TIn  message_in_type;

	typedef boost::function1<void, message_in_type> on_message_handler_type;
	typedef boost::function0<void> on_disconnected_handler_type;


	RateLimitedChannel(
				PolymorphicSharedPtr<Channel<TOut, TIn> > inToWrap,
				PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > inScheduler,
				boost::function1<double, TOut> inMessageCostFunOut,
				boost::function1<double, TIn> inMessageCostFunIn,
				int channelId
				) :
			mToWrap(inToWrap),
			mScheduler(inScheduler),
			mMessageCostFunOut(inMessageCostFunOut),
			mMessageCostFunIn(inMessageCostFunIn),
			mChannelId(channelId),
			mIsDisconnected(false)
		{
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		boost::mutex::scoped_lock lock(mMutex);

		return mScheduler->getScheduler();
		}

	virtual std::string channelType()
		{
		return "RateLimitedChannel<" + mToWrap->channelType() + ">";
		}

	void write(const message_out_type& in)
		{
			{
			boost::mutex::scoped_lock lock(mMutex);

			if (mIsDisconnected)
				throw ChannelDisconnected();
			}

		mScheduler->schedule(
			mMessageCostFunOut(in),
			mChannelId,
			boost::bind(
				&RateLimitedChannel::writeToChannel,
				mToWrap,
				in,
				weak_ptr_type(
					this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
					)
				)
			);
		}

	void disconnect()
		{
			{
			boost::mutex::scoped_lock lock(mMutex);

			if (mIsDisconnected)
				return;
			else
				mIsDisconnected = true;
			}

		mScheduler->dropGroup(mChannelId);

		mToWrap->disconnect();
		}

	virtual void setHandlers(
			on_message_handler_type inOnMessage,
			on_disconnected_handler_type inOnDisconnected
			)
		{
		mToWrap->setHandlers(
			boost::bind(
				&RateLimitedChannel::interiorReadMessageHandler,
				weak_ptr_type(
					this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
					),
				inOnMessage,
				boost::arg<1>()
				),
			boost::bind(
				&RateLimitedChannel::interiorChannelDisconnected,
				weak_ptr_type(
					this->polymorphicSharedPtrFromThis().template dynamic_pointer_cast<pointer_type>()
					)
				)
			);
		}

private:
	static void writeToChannel(
				PolymorphicSharedPtr<Channel<TOut, TIn> > channel,
				TOut message,
				weak_ptr_type weakThisPtr
				)
		{
		try {
			channel->write(message);
			}
		catch(ChannelDisconnected& d)
			{
			pointer_type p = weakThisPtr.lock();

			if (p && !p->mIsDisconnected)
				p->interiorDisconnected();
			}
		}

	static void interiorReadMessageHandler(
						weak_ptr_type self, 
						on_message_handler_type handler,
						TIn message
						)
		{
		pointer_type ptr = self.lock();

		if (!ptr)
			return;

		ptr->mScheduler->schedule(
			ptr->mMessageCostFunIn(message),
			ptr->mChannelId,
			boost::bind(handler, message)
			);
		}

	static void interiorChannelDisconnected(weak_ptr_type self)
		{
		pointer_type ptr = self.lock();

		if (!ptr)
			return;

		ptr->interiorDisconnected();
		}

	void interiorDisconnected()
		{
		boost::mutex::scoped_lock lock(mMutex);

		if (mIsDisconnected)
			return;

		mIsDisconnected = true;

		mScheduler->dropGroup(mChannelId);
		}

	boost::mutex mMutex;

	bool mIsDisconnected;

	PolymorphicSharedPtr<Channel<TOut, TIn> > mToWrap;

	PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > mScheduler;

	boost::function1<double, TOut> mMessageCostFunOut;

	boost::function1<double, TIn> mMessageCostFunIn;

	int mChannelId;
};



