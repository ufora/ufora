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


namespace Ufora {
namespace threading {

/***************

Gate allows threads to be blocked before passing through a 'gate'. Client threads
block if the gate is closed, and are allowed through if it's open. Controlling threads
may open or close the gate.

***************/

class Gate {
public:
	Gate() : 
			mIsOpen(true)
		{
		}

	Gate(bool isOpen) : 
			mIsOpen(isOpen)
		{
		}

	bool isOpen() const
		{
		boost::mutex::scoped_lock lock(mMutex);

		return mIsOpen;
		}

	//open the gate. Returns whether the gate was closed
	bool open()
		{
		boost::mutex::scoped_lock lock(mMutex);
		
		if (mIsOpen)
			return false;

		mIsOpen = true;

		mWaitingForGateToOpen.notify_all();

		return true;
		}

	//close the gate. Returns whether the gate was open
	bool close()
		{
		boost::mutex::scoped_lock lock(mMutex);
		
		if (!mIsOpen)
			return false;

		mIsOpen = false;

		return true;
		}

	void blockUntilOpen()
		{
		boost::mutex::scoped_lock lock(mMutex);

		while (!mIsOpen)
			mWaitingForGateToOpen.wait(lock);
		}

	bool blockUntilOpenWithTimeout(double timeoutSecs)
		{
		boost::mutex::scoped_lock lock(mMutex);

		if (!mIsOpen)
			mWaitingForGateToOpen.timed_wait(
				lock,
				boost::posix_time::milliseconds(timeoutSecs * 1000)
				);
		
		return mIsOpen;
		}

private:
	bool mIsOpen;

	boost::condition_variable mWaitingForGateToOpen;

	mutable boost::mutex mMutex;
};

}
}

