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

#include "Nullable.hpp"

template<class T, class scalar = double, bool compareValuesAsWell = false>
class Largest {
public:
	void observe(T value, scalar weight)
		{
		if (!mWeight || weight > *mWeight)
			{
			mWeight = weight;
			mValue = value;
			}
		}

	Nullable<T> largest() const
		{
		return mValue;
		}

	Nullable<scalar> largestWeight() const
		{
		return mWeight;
		}

private:
	Nullable<T> mValue;

	Nullable<scalar> mWeight;
};

template<class T, class scalar>
class Largest<T, scalar, true> {
public:
	void observe(T value, scalar weight)
		{
		if (!mWeight || weight > *mWeight || weight == *mWeight && *mValue < value)
			{
			mWeight = weight;
			mValue = value;
			}
		}

	Nullable<T> largest() const
		{
		return mValue;
		}

	Nullable<scalar> largestWeight() const
		{
		return mWeight;
		}

private:
	Nullable<T> mValue;

	Nullable<scalar> mWeight;
};
