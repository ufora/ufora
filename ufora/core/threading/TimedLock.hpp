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

#include <boost/thread.hpp>
#include "../Clock.hpp"
#include "../Logging.hpp"

class TimedLock {
public:
	TimedLock(boost::recursive_mutex& m, const char* lockType, double timeout = 1.0) : 
			preLockTimer(curClock()),
			mLock(m),
			postLockTimer(curClock()),
			mLockType(lockType),
			mTimeout(timeout),
			mUnlockStartTime(0),
			mTimesAcquired(1)
		{
		}
	~TimedLock()
		{
		if (curClock() - preLockTimer > mTimeout)
			LOG_WARN << mLockType << " mLock held for " << curClock() - postLockTimer 
				<< " over " << mTimesAcquired << " instances. acquiring took "
				<< postLockTimer - preLockTimer << ". trace =\n"
				<< Ufora::debug::StackTrace::getStringTrace();
		}

	void lock()
		{
		mTimesAcquired++;

		preLockTimer += curClock() - mUnlockStartTime;
		mLock.lock();
		postLockTimer += curClock() - mUnlockStartTime;
		}

	void unlock()
		{
		mUnlockStartTime = curClock();

		mLock.unlock();
		}

private:
	double preLockTimer;
	boost::recursive_mutex::scoped_lock mLock;
	double postLockTimer;

	const char* mLockType;

	double mTimeout;

	double mUnlockStartTime;

	long mTimesAcquired;
};
