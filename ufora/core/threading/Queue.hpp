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
#ifndef Queue_hpp_
#define Queue_hpp_

#include <boost/thread.hpp>
#include <deque>
#include "../math/Nullable.hpp"

template<class T>
class Queue {
public:
		void write(const T& in)
			{
			boost::mutex::scoped_lock lock(mMutex);
			mElements.push_back(in);

			mCondition.notify_one();
			}
		bool get(T& in)
			{
			boost::mutex::scoped_lock lock(mMutex);
			if (!mElements.size())
				return false;
			in = mElements.front();
			mElements.pop_front();
			return true;
			}
		Nullable<T>	getNonblock(void)
			{
			boost::mutex::scoped_lock lock(mMutex);

			if (mElements.size())
				{
				T tr = mElements.front();
				mElements.pop_front();
				return null() << tr;
				}
			return null();
			}

		T get(void)
			{
			boost::mutex::scoped_lock lock(mMutex);

			while (!mElements.size())
				mCondition.wait(lock);
			T tr = mElements.front();
			mElements.pop_front();
			return tr;
			}

		// gets with a timeout
		// returns false if the timeout was reached in which case
		// out is undefined.
		bool getTimeout(T& out, double timeoutSecs)
			{
			boost::mutex::scoped_lock lock(mMutex);

			bool retval = true;

			if (!mElements.size())
				{
				retval = mCondition.timed_wait(lock, boost::posix_time::milliseconds(timeoutSecs * 1000));

				if (!retval) // if we timed out then return false
					return retval;
				}

			if (!mElements.size())
				return false;

			out = mElements.front();
			mElements.pop_front();

			return retval;
			}
		void wait(void)
			{
			boost::mutex::scoped_lock lock(mMutex);

			while (!mElements.size())
				mCondition.wait(lock);
			}

		size_t size(void) const
			{
			boost::mutex::scoped_lock lock(mMutex);

			return mElements.size();
			}
private:
		mutable boost::mutex mMutex;
		std::deque<T> mElements;
		boost::condition_variable mCondition;
};


#endif

