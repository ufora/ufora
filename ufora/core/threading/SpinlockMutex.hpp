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

#include "../AtomicOps.hpp"

namespace Ufora {
namespace threading {

class Spinlock;

class SpinlockMutex {
public:
	typedef Spinlock scoped_lock;

	SpinlockMutex() : mLockState(0)
		{
		}

private:
	friend class Spinlock;

	AO_t mLockState;
};

class Spinlock {
public:
	Spinlock(SpinlockMutex& inMutex) : mState(inMutex.mLockState)
		{
		while (!AO_compare_and_swap_full(&mState, 0, 1))
			;
		mLocked = true;
		}

	~Spinlock()
		{
		if (mLocked)
			AO_store(&mState, 0);
		}

	void unlock()
		{
		if (mLocked)
			{
			mLocked = false;
			AO_store(&mState, 0);
			}
		}

	void lock()
		{
		if (!mLocked)
			{
			mLocked = true;

			while (!AO_compare_and_swap_full(&mState, 0, 1))
				;
			}
		}
private:
	AO_t& mState;
	bool mLocked;
};


}
}

