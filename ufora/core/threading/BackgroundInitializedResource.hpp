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

#include <stdexcept>
#include <boost/thread.hpp>
#include <boost/thread/condition.hpp>
#include "../math/Nullable.hpp"
#include "../Clock.hpp"

//model for a value that gets initialized (once) by some
//background process. Clients who try to access it will block if
//it hasn't been initialized. If it has been invalidated, any
//calls to get() that are pending or made in the future will throw an 
//exception. getNonblocking is unchanged since it makes no guarantees.

template<class T>
class BackgroundInitializedResource {
public:
	BackgroundInitializedResource() : mInvalid(false) {}
	//used to set the state to invalid and wake up any waiting threads
	void invalidate(void)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);
        mInvalid = true;
		mCondition.notify_all();
		}

    //this makes no guarantees about validity
	Nullable<T>	getNonblocking(void) const
		{
		return mValue;
		}
	//reset the value to some new state. It must already have a value.
	void reset(const T& in)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		lassert(mValue);

		mValue = in;

		mCondition.notify_all();
		}
	
	//set the value. it must never have been set before.
	void set(const T& in)
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		lassert(!mValue);

		mValue = in;

		mCondition.notify_all();
		}

	const T& get(void) const
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (!mValue && !mInvalid)
			mCondition.wait(lock);
		if (mInvalid)
			throw std::logic_error("BackgroundInitializedResource is no longer valid");
		return *mValue;
		}

	//waits until the value is set or a timeout elapses
	Nullable<T> waitTimeout(double timeoutSecs) const
		{
		boost::recursive_mutex::scoped_lock lock(mMutex);

		if (!mValue)
			{
			mCondition.timed_wait(lock, boost::posix_time::milliseconds(timeoutSecs * 1000));
			}

		return mValue;
		}

private:
	mutable boost::recursive_mutex 	mMutex;
	mutable boost::condition 		mCondition;
	Nullable<T> 		 			mValue;
	bool							mInvalid;
};

