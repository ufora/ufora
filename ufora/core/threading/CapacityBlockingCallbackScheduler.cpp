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
#include "CapacityBlockingCallbackScheduler.hpp"


CapacityBlockingCallbackScheduler::CapacityBlockingCallbackScheduler(
													PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler, 
													uint64_t inMaxCapacity
													) : 
				mMaxCapacity(inMaxCapacity),
				mCurSizeScheduled(0),
				mCallbackScheduler(inCallbackScheduler)
	{
	}

void CapacityBlockingCallbackScheduler::scheduleButBlockIfCapacityIsExceeded(
														boost::function0<void> inFunc, 
														uint64_t inSize
														)
	{
	boost::mutex::scoped_lock lock(mMutex);

	while (mCurSizeScheduled >= mMaxCapacity)
		mCurCapacityChanged.wait(lock);

	mCurSizeScheduled += inSize;
	mCallbackScheduler->scheduleImmediately(
		boost::bind(
			&CapacityBlockingCallbackScheduler::callAndDecrementCapacity,
			this,
			inFunc,
			inSize
			),
		"callAndDecrementCapacity"
		);
	}

void CapacityBlockingCallbackScheduler::callAndDecrementCapacity(
														boost::function0<void> inFunc, 
														uint64_t capacity
														)
	{
	try {
		inFunc();
		}
	catch(...)
		{
		decrementCapacity(capacity);
		throw;
		}

	decrementCapacity(capacity);
	}

void CapacityBlockingCallbackScheduler::decrementCapacity(uint64_t capacity)
	{
	boost::mutex::scoped_lock lock(mMutex);
	
	mCurSizeScheduled -= capacity;

	mCurCapacityChanged.notify_all();
	}

void CapacityBlockingCallbackScheduler::setMaxCapacity(uint64_t inNewCapacity)	
	{
	boost::mutex::scoped_lock lock(mMutex);
	
	mMaxCapacity = inNewCapacity;

	mCurCapacityChanged.notify_all();
	}

uint64_t CapacityBlockingCallbackScheduler::getMaxCapacity(void) const
	{
	return mMaxCapacity;
	}

bool CapacityBlockingCallbackScheduler::blockUntilPendingHaveExecuted()
	{
	return mCallbackScheduler->blockUntilPendingHaveExecuted();
	}

bool CapacityBlockingCallbackScheduler::blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty()
	{
	return mCallbackScheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();
	}

bool CapacityBlockingCallbackScheduler::blockUntilPendingHaveExecutedAndQueueIsEmpty(bool logDelays)
	{
	return mCallbackScheduler->blockUntilPendingHaveExecutedAndQueueIsEmpty(logDelays);
	}

