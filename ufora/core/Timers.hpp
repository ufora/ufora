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
#ifndef Timers_hpp_
#define Timers_hpp_

#include "math/StatisticsAccumulator.hpp"
#include "Clock.hpp"

class ExclusiveTimer;

template<class T, class scalar_type>
class ExclusiveStatTimer;

class TimingExclusion {
public:
		TimingExclusion()
			{
			currentlyComputing = 0;
			}
private:
		friend class ExclusiveTimer;


		template<class T, class scalar_type>
		friend class ExclusiveStatTimer;

		double* currentlyComputing;
};

class ExclusiveTimer {
public:
		ExclusiveTimer(double& output, TimingExclusion& ex, bool inActive = true) : out(output), mEx(ex), mActive(inActive)
			{
			if (mActive)
				{
				t0 = curClock();
				tOrig = t0;

				priorComputing = mEx.currentlyComputing;
				mEx.currentlyComputing = &t0;
				}
			}
		ExclusiveTimer(TimingExclusion& ex, double& output, bool inActive = true) : out(output), mEx(ex), mActive(inActive)
			{
			if (mActive)
				{
				t0 = curClock();
				tOrig = t0;

				priorComputing = mEx.currentlyComputing;
				mEx.currentlyComputing = &t0;
				}
			}
		~ExclusiveTimer()
			{
			if (mActive)
				{
				double cc = curClock();
				out += cc - t0;
				if (priorComputing)
					*priorComputing += cc - tOrig;
				mEx.currentlyComputing = priorComputing;
				}
			}
private:
		double& out;
		double t0;
		double tOrig;
		double* priorComputing;
		bool mActive;
		TimingExclusion& mEx;
};

template<class T, class scalar_type>
class ExclusiveStatTimer {
public:
		ExclusiveStatTimer(StatisticsAccumulator<T, scalar_type>& output, TimingExclusion& ex, bool inActive = true) : out(output), mEx(ex), mActive(inActive)
			{
			if (mActive)
				{
				t0 = curClock();
				tOrig = t0;

				priorComputing = mEx.currentlyComputing;
				mEx.currentlyComputing = &t0;
				}
			}
		ExclusiveStatTimer(TimingExclusion& ex, StatisticsAccumulator<T, scalar_type>& output, bool inActive = true) : out(output), mEx(ex), mActive(inActive)
			{
			if (mActive)
				{
				t0 = curClock();
				tOrig = t0;

				priorComputing = mEx.currentlyComputing;
				mEx.currentlyComputing = &t0;
				}
			}
		~ExclusiveStatTimer()
			{
			if (mActive)
				{
				double cc = curClock();
				out.observe(cc - t0 - 0.0000015, 1.0);
				if (priorComputing)
					*priorComputing += cc - tOrig + 0.0000015;
				mEx.currentlyComputing = priorComputing;
				}
			}
private:
		StatisticsAccumulator<T, scalar_type>& out;
		double t0;
		double tOrig;
		double* priorComputing;
		bool mActive;
		TimingExclusion& mEx;
};


#endif

