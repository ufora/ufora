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

#include "Clock.hpp"

namespace Ufora {

class ScopedTimingAccumulator {
public:
	ScopedTimingAccumulator() : 
			mTimeElapsed(0),
			mCount(0)
		{
		}

	void observe(double timeElapsed)
		{
		mTimeElapsed += timeElapsed;
		mCount++;
		}

	double total() const
		{
		return mTimeElapsed;
		}

	long count() const
		{
		return mCount;
		}

	double average() const
		{
		if (mCount == 0)
			return 0.0;

		return mTimeElapsed / mCount;
		}

	template<class callback_type>
	class Scope {
	public:
		Scope(ScopedTimingAccumulator& accumulator, const callback_type& callback) : 
				mT0(curClock()),
				mAccumulator(accumulator),
				mCallback(callback)
			{
			}

		~Scope()
			{
			ScopedTimingAccumulator old = mAccumulator;

			mAccumulator.observe(curClock() - mT0);

			mCallback(old, mAccumulator);
			}

	private:
		double mT0;

		ScopedTimingAccumulator& mAccumulator;

		callback_type mCallback;
	};

	template<class callback_type>
	Scope<callback_type> scope(const callback_type& c)
		{
		return Scope<callback_type>(*this, c);
		}

	class NoCallback {
	public:
		void operator()(const ScopedTimingAccumulator& original, 
						const ScopedTimingAccumulator& final)
			{
			}
	};

	Scope<NoCallback> scope()
		{
		return scope(NoCallback());
		}

private:
	double mTimeElapsed;
	
	long mCount;
};

}
