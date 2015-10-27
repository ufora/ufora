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
#include "RateLimitedChannel.hpp"

/*************************

RateLimitedChannelGroup allows a set of channels to have their messages 'throttled', as if they
were going through a real network.  Clients hand the group a real channel, we return a
throttled channel.

**************************/

template<class TOut, class TIn>
class RateLimitedChannelGroup : 
						public PolymorphicSharedPtrBase<RateLimitedChannelGroup<TOut, TIn> > {
public:
	typedef PolymorphicSharedPtr<RateLimitedChannelGroup<TOut, TIn> > pointer_type;

	typedef PolymorphicSharedWeakPtr<RateLimitedChannelGroup<TOut, TIn> > weak_ptr_type;
	
	RateLimitedChannelGroup(
				PolymorphicSharedPtr<CallbackScheduler> inScheduler,
				boost::function1<double, TOut> messageCostFunOut,
				boost::function1<double, TIn> messageCostFunIn,
				double throughput
				) :
			mScheduler(
				new RateLimitedCallbackScheduler<int>(
					inScheduler,
					throughput
					)
				),
			mCurChannelId(0),
			mMessageCostFunOut(messageCostFunOut),
			mMessageCostFunIn(messageCostFunIn)
		{
		}

	PolymorphicSharedPtr<Channel<TOut, TIn> > wrap(PolymorphicSharedPtr<Channel<TOut, TIn> > inChannel)
		{
		boost::mutex::scoped_lock lock(mMutex);

		mCurChannelId++;

		return PolymorphicSharedPtr<Channel<TOut, TIn> >(
			new RateLimitedChannel<TOut, TIn>(
				inChannel,
				mScheduler,
				mMessageCostFunOut,
				mMessageCostFunIn,
				mCurChannelId
				)
			);
		}


private:
	boost::mutex mMutex;

	long mCurChannelId;

	boost::function1<double, TOut> mMessageCostFunOut;

	boost::function1<double, TIn> mMessageCostFunIn;

	PolymorphicSharedPtr<RateLimitedCallbackScheduler<int> > mScheduler;
};


