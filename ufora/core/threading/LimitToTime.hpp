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

#include "Queue.hpp"
#include "../Logging.hpp"
#include "../Clock.hpp"
#include <boost/thread.hpp>

class LimitToTime {
public:
	LimitToTime(double maxTime) 
		{
		curQueue().write(std::make_pair(this, curClock() + maxTime));
		ensureStarted();
		}

	~LimitToTime()
		{
		curQueue().write(std::make_pair(this, 0));
		}

private:
	static void threadLoop()
		{
		std::map<LimitToTime*, double> timeouts;

		while (true)
			{
			std::pair<LimitToTime*, double> timeout;

			if (curQueue().getTimeout(timeout, 1))
				{
				if (timeouts.find(timeout.first) == timeouts.end())
					timeouts[timeout.first] = timeout.second;
				else
					timeouts.erase(timeout.first);
				}

			for (auto timeoutAndTime: timeouts)
				if (curClock() > timeoutAndTime.second)
					{
					LOG_CRITICAL << "Timed out!";
					fflush(stdout);
					fflush(stderr);

					asm("int3");
					}
			}	
		}

	static void ensureStarted()
		{
		static bool isStarted = false;
		static boost::mutex mutex;

		boost::mutex::scoped_lock lock(mutex);
		if (!isStarted)
			{
			boost::thread(&threadLoop).detach();
			isStarted = true;
			}
		}

	static Queue<std::pair<LimitToTime*, double> >& curQueue()
		{
		static Queue<std::pair<LimitToTime*, double> > queue;

		return queue;
		}
};

