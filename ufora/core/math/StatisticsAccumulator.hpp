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
#ifndef StatisticsAccumulator_H_
#define StatisticsAccumulator_H_

#include "../serialization/Serialization.hpp"

template<class T, class scalar_type>
class StatisticsAccumulator {
public:
		StatisticsAccumulator()
			{
			mW = 0.0;
			mFirstX = T();
			mXW = T();
			mXXW = T();
			}
		StatisticsAccumulator(const StatisticsAccumulator& in)
			{
			mFirstX = in.mFirstX;
			mW = in.mW;
			mXW = in.mXW;
			mXXW = in.mXXW;
			}
		StatisticsAccumulator& operator=(const StatisticsAccumulator& in)
			{
			mFirstX = in.mFirstX;
			mW = in.mW;
			mXW = in.mXW;
			mXXW = in.mXXW;

			return *this;
			}

		void	observe(const T& inX, const scalar_type& inWeight)
			{
			if (mW == 0.0)
				mFirstX = inX;

			mW += inWeight;
			mXW += (inX - mFirstX) * inWeight;
			mXXW += (inX - mFirstX) * (inX - mFirstX) * inWeight;
			}
		T	variance(void) const
			{
			return (mXXW / mW - mXW * mXW / mW / mW);
			}
		T	mean(void) const
			{
			return mXW / mW + mFirstX;
			}
		T	meanFrom(const T& inCenter) const
			{
			return mXW / mW + (mFirstX - inCenter);
			}
		scalar_type	weight(void) const
			{
			return mW;
			}
		scalar_type	getXW(void) const
			{
			return mXW + mFirstX * mW;
			}
		void	scaleWeight(scalar_type in)
			{
			mW *= in;
			mXW *= in;
			}
		void	scaleXVal(scalar_type in)
			{
			mFirstX *= in;
			mXW *= in;
			}
		StatisticsAccumulator&	operator+=(const StatisticsAccumulator& in)
			{
			mXW += in.mXW;
			T t = (in.mFirstX - mFirstX);
			t *= in.mW;
			mXW += t;
			mW += in.mW;
			mXXW += in.mXXW;

			return *this;
			}
		template<class storage_type>
		void serialize(storage_type& s) const
			{
			s.serialize(mFirstX);
			s.serialize(mXW);
			s.serialize(mW);
			s.serialize(mXXW);
			}
		template<class storage_type>
		void deserialize(storage_type& s)
			{
			s.deserialize(mFirstX);
			s.deserialize(mXW);
			s.deserialize(mW);
			s.deserialize(mXXW);
			}
private:
		T				mFirstX;
		T				mXW;
		T				mXXW;
		scalar_type		mW;
};

template<class T, class scalar_type, class storage_type>
class Serializer<StatisticsAccumulator<T, scalar_type>, storage_type> {
public:
		static void serialize(storage_type& s, const StatisticsAccumulator<T, scalar_type>& in)
			{
			in.serialize(s);
			}
};

template<class T, class scalar_type, class storage_type>
class Deserializer<StatisticsAccumulator<T, scalar_type>, storage_type> {
public:
		static void deserialize(storage_type& s, StatisticsAccumulator<T, scalar_type>& in)
			{
			in.deserialize(s);
			}
};

#endif

