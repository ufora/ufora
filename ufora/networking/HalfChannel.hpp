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
#include "../core/threading/CallbackScheduler.hppml"

template<class TOut, class TIn>
class HalfChannel : public Channel<TOut, TIn> {
public:
	typedef PolymorphicSharedPtr<
		HalfChannel<TOut, TIn>,
		typename Channel<TOut, TIn>::pointer_type
		> pointer_type;

	typedef PolymorphicSharedWeakPtr<
		HalfChannel<TOut, TIn>,
		typename Channel<TOut, TIn>::weak_ptr_type
		> weak_ptr_type;


	HalfChannel(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				boost::function1<void, TOut> inWriteCallback,
				boost::function0<void> inOnDisconnected
				) :
			mCallbackScheduler(inCallbackScheduler),
			mHasHandlers(false),
			mIsDisconnected(false),
			mWriteCallback(inWriteCallback),
			mOnDisconnected2(inOnDisconnected)
		{

		}

	virtual std::string channelType()
		{
		return "HalfChannel";
		}

	virtual ~HalfChannel()
		{
		}

	virtual void write(const TOut& in)
		{
		boost::mutex::scoped_lock lock(mMutex);

		if (mIsDisconnected)
			throw ChannelDisconnected();

		mCallbackScheduler->scheduleImmediately(
			boost::bind(
				mWriteCallback,
				in
				),
			"HalfChannel::write"
			);
		}

	virtual void disconnect()
		{
		boost::mutex::scoped_lock lock(mMutex);

		if (!mIsDisconnected)
			{
			mIsDisconnected = true;
			mOnDisconnected2();

			if (mHasHandlers)
				mOnDisconnected();
			}
		}

	virtual void setHandlers(
				boost::function1<void, TIn> inOnMessage,
				boost::function0<void> inOnDisconnected
				)
		{
		boost::mutex::scoped_lock lock(mMutex);

		mOnDisconnected = inOnDisconnected;
		mOnMessage = inOnMessage;

		mHasHandlers = true;

		while (mPending.size())
			mCallbackScheduler->scheduleImmediately(
				boost::bind(
					mOnMessage,
					mPending.get()
					),
				"HalfChannel::setHandlers"
				);
		}

	void receive(TIn in)
		{
		boost::mutex::scoped_lock lock(mMutex);

		if (mHasHandlers)
			mCallbackScheduler->scheduleImmediately(
				boost::bind(
					mOnMessage,
					in
					),
				"HalfChannel::receive"
				);
		else
			mPending.write(in);
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
	PolymorphicSharedPtr<CallbackScheduler> mCallbackScheduler;

	boost::mutex mMutex;

	Queue<TIn> mPending;

	bool mHasHandlers;

	bool mIsDisconnected;

	boost::function1<void, TIn> mOnMessage;

	boost::function0<void> mOnDisconnected;

	boost::function1<void, TOut> mWriteCallback;

	boost::function0<void> mOnDisconnected2;
};


