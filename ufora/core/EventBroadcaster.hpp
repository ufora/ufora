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

#include <boost/bind.hpp>
#include <boost/thread.hpp>
#include <set>
#include "debug/StackTrace.hpp"
#include "threading/CallbackScheduler.hppml"
#include "Clock.hpp"
#include "PolymorphicSharedPtr.hpp"
#include <iostream>
#include "cppml/CPPMLPrettyPrinter.hppml"
#include <deque>
#include "AtomicOps.hpp"

/*******

A broadcaster that allows clients to subscribe to events using callbacks.

This class is threadsafe. Events are fired on the CallbackScheduler, so calling 'broadcast'
is nonblocking.

*******/

template<class event_type>
class EventBroadcaster {
public:
	EventBroadcaster(PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler, std::string inName = "") : 
			mScheduler(inCallbackScheduler),
			mBroadcasterName(inName),
			mIsSuspended(false),
			mPendingEventCount(new AO_t(0))
		{
		if (mBroadcasterName.size() == 0)
			mBroadcasterName = Ufora::debug::StackTrace::demangle(typeid(EventBroadcaster<event_type>).name());

		mEventSchedulers.push_back(
			boost::bind(
				boost::function2<bool, boost::shared_ptr<AO_t>, event_type>(
					[](boost::shared_ptr<AO_t> in, event_type e) {
						AO_fetch_and_add_full(&*in, -1);

						return true;
						}
					),
				mPendingEventCount,
				boost::arg<1>()
				)
			);
		}

	void suspend()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mIsSuspended = true;
		}

	void resume()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mIsSuspended = false;

		while (mSuspendedEvents.size())
			{
			for (long k = 0; k < mEventSchedulers.size();k++)
				if (!mEventSchedulers[k](mSuspendedEvents.front()))
					{
					mEventSchedulers.erase(mEventSchedulers.begin() + k);
					k--;
					}
			mSuspendedEvents.pop_front();
			}
		}

	bool isSuspended()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		return mIsSuspended;
		}

	void clearSchedulers()
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		mEventSchedulers.clear();
		}

	AO_t pendingEventCount() const
		{
		return AO_load(&*mPendingEventCount);
		}

	void broadcast(const event_type& inEvent)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		AO_fetch_and_add_full(&*mPendingEventCount, 1);

		if (mIsSuspended)
			{
			mSuspendedEvents.push_back(inEvent);
			return;
			}

		for (long k = 0; k < mEventSchedulers.size();k++)
			if (!mEventSchedulers[k](inEvent))
				{
				mEventSchedulers.erase(mEventSchedulers.begin() + k);
				k--;
				}
		}

	template<class T, class base_type>
	void subscribe(
				PolymorphicSharedWeakPtr<T, base_type> inWeakPtr, 
				void (T::* callbackPtr)(event_type)
				)
		{
		typedef PolymorphicSharedWeakPtr<T, base_type> weak_ptr_type;

		using namespace boost;

		subscribe(
			boost::bind(
				&scheduleForPtrMemberFcn<T, weak_ptr_type>, 
				mScheduler,
				inWeakPtr, 
				callbackPtr, 
				mBroadcasterName,
				_1
				)
			);
		}

	template<class T, class base_type, class arg_type>
	void subscribe(
				PolymorphicSharedWeakPtr<T, base_type> inWeakPtr, 
				void (T::* callbackPtr)(arg_type, event_type),
				arg_type arg
				)
		{
		typedef PolymorphicSharedWeakPtr<T, base_type> weak_ptr_type;

		using namespace boost;

		subscribe(
			boost::bind(
				&scheduleForPtrMemberFcn2<T, weak_ptr_type, arg_type>, 
				mScheduler,
				inWeakPtr, 
				callbackPtr, 
				mBroadcasterName,
				arg,
				_1
				)
			);
		}

	template<class T, class base_type>
	void subscribe(
				PolymorphicSharedWeakPtr<T, base_type> inWeakPtr, 
				boost::function2<void, T*, event_type> inCallback
				)
		{
		typedef PolymorphicSharedWeakPtr<T, base_type> weak_ptr_type;

		using namespace boost;

		subscribe(
			boost::bind(
				&scheduleForPtrBoostFcn<T, weak_ptr_type>, 
				mScheduler,
				inWeakPtr, 
				inCallback,
				mBroadcasterName, 
				_1
				)
			);
		}

	template<class T, class base_type>
	void subscribe(
				PolymorphicSharedPtr<T, base_type> inPtr, 
				void (T::* callbackPtr)(event_type)
				)
		{
		typedef typename PolymorphicSharedPtr<T, base_type>::weak_ptr_type weak_ptr_type;

		subscribe(weak_ptr_type(inPtr), callbackPtr);
		}

	template<class T, class base_type>
	void subscribe(
				PolymorphicSharedPtr<T, base_type> inPtr, 
				boost::function2<void, T*, event_type> inCallback
				)
		{
		typedef typename PolymorphicSharedPtr<T, base_type>::weak_ptr_type weak_ptr_type;

		subscribe(weak_ptr_type(inPtr), inCallback);
		}

	void subscribe(boost::function1<bool, event_type> callback)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		//insert one behind the event counter decrement scheduler.
		mEventSchedulers.insert(mEventSchedulers.begin() + mEventSchedulers.size() - 1, callback);
		}

	int subscribers(void) const
		{
		return mEventSchedulers.size();
		}

	//this has to have a different signature thatn boost::function1<bool, event_type> because
	//the two function types are (unfortunately) convertible to each other
	void subscribeForever(boost::function1<void, event_type> callback)
		{
		subscribe(
			boost::bind(
				&callCallbackAndReturnTrue,
				callback,
				boost::arg<1>()
				)
			);
		}

private:
	static bool callCallbackAndReturnTrue(boost::function1<void, event_type> callback, event_type e)
		{
		callback(e);

		return true;
		}


	template<class T, class weak_ptr_type>
	static void broadcastToWeakPtrMemberFcn(
						weak_ptr_type inPtr,
						void (T::* callbackPtr)(event_type),
						event_type inEvent
						)
		{
		typedef typename weak_ptr_type::strong_ptr_type strong_ptr_type;

		strong_ptr_type ptr = inPtr.lock();
		
		if (!ptr)
			return;

		( (*ptr).*callbackPtr)(inEvent);
		}

	template<class T, class weak_ptr_type, class arg_type>
	static void broadcastToWeakPtrMemberFcn2(
						weak_ptr_type inPtr,
						void (T::* callbackPtr)(arg_type, event_type),
						event_type inEvent,
						arg_type inArg
						)
		{
		typedef typename weak_ptr_type::strong_ptr_type strong_ptr_type;

		strong_ptr_type ptr = inPtr.lock();
		
		if (!ptr)
			return;

		( (*ptr).*callbackPtr)(inArg, inEvent);
		}

	template<class T, class weak_ptr_type>
	static bool scheduleForPtrMemberFcn(
						PolymorphicSharedPtr<CallbackScheduler> scheduler,
						weak_ptr_type weakPtr,
						void (T::* callbackPtr)(event_type),
						std::string inBroadcasterName,
						event_type inEvent
						)
		{
		typedef typename weak_ptr_type::strong_ptr_type strong_ptr_type;

		if (weakPtr.expired())
			return false;
		else
			{
			scheduler->scheduleImmediately(
				boost::bind(
					&broadcastToWeakPtrMemberFcn<T, weak_ptr_type>,
					weakPtr,
					callbackPtr,
					inEvent
					),
				inBroadcasterName
				);

			return true;
			}
		}

	template<class T, class weak_ptr_type, class arg_type>
	static bool scheduleForPtrMemberFcn2(
						PolymorphicSharedPtr<CallbackScheduler> scheduler,
						weak_ptr_type weakPtr,
						void (T::* callbackPtr)(arg_type, event_type),
						std::string inBroadcasterName,
						arg_type inArg,
						event_type inEvent
						)
		{
		typedef typename weak_ptr_type::strong_ptr_type strong_ptr_type;

		if (weakPtr.expired())
			return false;
		else
			{
			scheduler->scheduleImmediately(
				boost::bind(
					&broadcastToWeakPtrMemberFcn2<T, weak_ptr_type, arg_type>,
					weakPtr,
					callbackPtr,
					inEvent,
					inArg
					),
				inBroadcasterName
				);

			return true;
			}
		}

	template<class T, class ptr_type>
	static void broadcastToPtrBoostFcn(
						ptr_type inPtr,
						boost::function2<void, T*, event_type> callback,
						event_type inEvent
						)
		{
		callback(&*inPtr, inEvent);
		}

	template<class T, class weak_ptr_type>
	static bool scheduleForPtrBoostFcn(
						PolymorphicSharedPtr<CallbackScheduler> scheduler,
						weak_ptr_type weakPtr,
						boost::function2<void, T*, event_type> callback,
						std::string inBroadcasterName,
						event_type inEvent
						)
		{
		typedef typename weak_ptr_type::strong_ptr_type strong_ptr_type;

		strong_ptr_type ptr = weakPtr.lock();

		if (!ptr)
			return false;
		else
			{
			scheduler->scheduleImmediately(
				boost::bind(
					&broadcastToPtrBoostFcn<T, strong_ptr_type>,
					ptr,
					callback,
					inEvent
					),
				inBroadcasterName
				);

			return true;
			}
		}

	std::vector<boost::function1<bool, event_type> > mEventSchedulers;

	std::string mBroadcasterName;

	boost::recursive_mutex mMutex;

	PolymorphicSharedPtr<CallbackScheduler> mScheduler;

	bool mIsSuspended;

	std::deque<event_type> mSuspendedEvents;

	boost::shared_ptr<AO_t> mPendingEventCount;
};







