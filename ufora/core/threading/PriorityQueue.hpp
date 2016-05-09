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
#ifndef PriorityQueue_hpp_
#define PriorityQueue_hpp_

#include <boost/thread.hpp>
#include "../math/Nullable.hpp"

/********
PriorityQueue

allows several threads to read from a queue and only accept items above a
given 'priority' level. The queue always pops an element of the highest possible
priority, and the order is nondeterministic within the priority level.

'T' must be orderable.
********/

template<class T, class priority_type = int>
class PriorityQueue {
public:
		void write(const T& in, priority_type inPriority)
			{
			boost::mutex::scoped_lock lock(mMutex);
			mElements[inPriority].insert(in);
			mPriorities[in] = inPriority;

			mCondition.notify_all();
			}
		//returns true if the item exists and was sucessfully reprioritized
		bool reprioritize(const T& in, priority_type inPriority)
			{
			boost::mutex::scoped_lock lock(mMutex);

			if (mPriorities.find(in) != mPriorities.end())
				{
				priority_type oldPriority = mPriorities.find(in)->second;

				mElements[oldPriority].erase(in);
				mPriorities[in] = inPriority;
				mElements[inPriority].insert(in);

				mCondition.notify_all();
				return true;
				}

			return false;
			}

		long size()
			{
			boost::mutex::scoped_lock lock(mMutex);
			return mPriorities.size();
			}

		Nullable<priority_type> getPriority(const T& in)
			{
			boost::mutex::scoped_lock lock(mMutex);

			if (mPriorities.find(in) != mPriorities.end())
				return null() << mPriorities[in];
			return null();
			}
		Nullable<T>	getNonblock(priority_type priorityOrHigher)
			{
			boost::mutex::scoped_lock lock(mMutex);

			T tr;
			if (get(tr, priorityOrHigher))
				return null() << tr;
			return null();
			}

		T get(priority_type priorityOrHigher)
			{
			boost::mutex::scoped_lock lock(mMutex);

			T tr;
			while (!get(tr, priorityOrHigher))
				mCondition.wait(lock);

			return tr;
			}
private:
		//expects you to have a lock when you call it. returns 'true' if you
		//get anything out
		bool get(T& in, priority_type priorityOrHigher)
			{
			for (typename map<priority_type, set<T> >::reverse_iterator
						it = mElements.rbegin(),
						it_end = mElements.rend();
					it != it_end;
					++it)
				if (it->first < priorityOrHigher)
					return false;
					else
				if (it->second.size())
					{
					in = *it->second.begin();
					it->second.erase(it->second.begin());
					mPriorities.erase(in);
					return true;
					}

			return false;
			}

		boost::mutex mMutex;
		map<priority_type, std::set<T> > 		mElements;
		map<T, priority_type> 					mPriorities;
		boost::condition_variable 				mCondition;
};


#endif

