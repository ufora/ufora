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

#include <vector>
#include "../core/threading/Queue.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "Channel.hpp"

/********* InMemoryChannel
 *
 * Comes in std::pairs. If one channel is destroyed, it writes "null" to the other channel, 
 * indicating that the channels are no longer connected.  
 * The other channel puts any nulls back on the queue to indicate that the channel is permenantly 
 * disconnected.
 *****************************/


template<class T>
class InMemoryChannelCallbacks {
public:
	InMemoryChannelCallbacks(PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler) : 
			mCallbackScheduler(inCallbackScheduler),
			mCallbacksAreSet(false),
			mIsDisconnected(false)
		{
		}

	void setHandlers(
			boost::function1<void, T> inOnMessage, 
			boost::function0<void> inOnDisconnected
			)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mOnMessageReceived = inOnMessage;
		mOnDisconnected = inOnDisconnected;

		mCallbacksAreSet = true;

		bool wasDisconnected = mIsDisconnected;

		Nullable<T> val;

		while (val = mUnconsumedMessages.getNonblock())
			mCallbackScheduler->scheduleImmediately(
				boost::bind(
					mOnMessageReceived,
					*val
					),
				"InMemoryChannelCallbacks::setHandlers"
				);

		if (wasDisconnected)
			mCallbackScheduler->scheduleImmediately(
					mOnDisconnected, "InMemoryChannel::setHandlers disconnect");
		}

	void onMessageReceived(const T& in)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (!mCallbacksAreSet)
			{
			if (mIsDisconnected)
				return;

			mUnconsumedMessages.write(in);
			return;
			}
		
		mCallbackScheduler->scheduleImmediately(
			boost::bind(mOnMessageReceived, in),
			"InMemoryChannel::onMessageReceived"
			);
		}

	void disconnect()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (mIsDisconnected || !mCallbacksAreSet)
			{
			mIsDisconnected = true;
			return;
			}

		mCallbackScheduler->scheduleImmediately(mOnDisconnected, "InMemoryChannel::disconnect");
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mCallbackScheduler = inScheduler;
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		return mCallbackScheduler;
		}

private:
	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	bool mCallbacksAreSet;

	bool mIsDisconnected;

	Queue<T> mUnconsumedMessages;

	boost::function1<void, T> mOnMessageReceived;
	
	boost::function0<void> mOnDisconnected;

	boost::recursive_mutex mMutex;
};

class InMemoryChannelDisconnectFlag {
public:
	InMemoryChannelDisconnectFlag() : isDisconnected(false)
		{
		}

	bool isDisconnected;

	boost::recursive_mutex mutex;
};

template<class TOut, class TIn>
class InMemoryChannel : public Channel<TOut, TIn> {

	typedef InMemoryChannelCallbacks<TOut> OutputCallbacks;

	typedef InMemoryChannelCallbacks<TIn> InputCallbacks;

public:
	typedef PolymorphicSharedPtr<
		InMemoryChannel<TOut, TIn>, 
		typename Channel<TOut, TIn>::pointer_type
		> pointer_type;

	typedef PolymorphicSharedWeakPtr<
		InMemoryChannel<TOut, TIn>, 
		typename Channel<TOut, TIn>::weak_ptr_type
		> weak_ptr_type;
	
	InMemoryChannel(
				boost::shared_ptr<OutputCallbacks> inOutputCallbacks,
				boost::shared_ptr<InputCallbacks> inInputCallbacks,
				boost::shared_ptr<InMemoryChannelDisconnectFlag> inDisconnected
				) :
			mOutputCallbacks(inOutputCallbacks), 
			mInputCallbacks(inInputCallbacks),
			mDisconnected(inDisconnected)

		{
		}

	~InMemoryChannel()
		{
		try {
			disconnect();
			}
		catch(...)
			{
			}
		}

	virtual std::string channelType()
		{
		return "InMemoryChannel";
		}

	virtual void disconnect(void)
		{
			{
			boost::recursive_mutex::scoped_lock lock(mDisconnected->mutex);

			if (mDisconnected->isDisconnected)
				return;

			mDisconnected->isDisconnected = true;
			}
		
		mInputCallbacks->disconnect();
		mOutputCallbacks->disconnect();
		}

	virtual void write(const TOut& message)
		{
			{
			boost::recursive_mutex::scoped_lock lock(mDisconnected->mutex);
		
			if (mDisconnected->isDisconnected)
				throw ChannelDisconnected();
			}

		mOutputCallbacks->onMessageReceived(message);
		}

	static std::pair<typename InMemoryChannel<TOut, TIn>::pointer_type, 
					 typename InMemoryChannel<TIn, TOut>::pointer_type> createChannelPair(
							 PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler)
		{
		boost::shared_ptr<OutputCallbacks> output(new OutputCallbacks(inCallbackScheduler));
		boost::shared_ptr<InputCallbacks> input(new InputCallbacks(inCallbackScheduler));
		boost::shared_ptr<InMemoryChannelDisconnectFlag> disconnected(new InMemoryChannelDisconnectFlag());
				
		return std::make_pair(
						typename InMemoryChannel<TOut, TIn>::pointer_type(
							new InMemoryChannel<TOut, TIn>(output, input, disconnected)
							),
						typename InMemoryChannel<TIn, TOut>::pointer_type(
							new InMemoryChannel<TIn, TOut>(input, output, disconnected)
							)
						);
		}


	virtual void setHandlers(
			boost::function1<void, TIn> inOnMessage, 
			boost::function0<void> inOnDisconnected
			)
		{
		mInputCallbacks->setHandlers(inOnMessage, inOnDisconnected);
		}

	void setCallbackScheduler(PolymorphicSharedPtr<CallbackScheduler> inScheduler)
		{
		mOutputCallbacks->setCallbackScheduler(inScheduler);
		mInputCallbacks->setCallbackScheduler(inScheduler);
		}

	PolymorphicSharedPtr<CallbackScheduler> getScheduler()
		{
		return mInputCallbacks->getScheduler();
		}

private:
	boost::shared_ptr<OutputCallbacks> mOutputCallbacks;

	boost::shared_ptr<InputCallbacks> mInputCallbacks;

	boost::shared_ptr<InMemoryChannelDisconnectFlag> mDisconnected;
};


