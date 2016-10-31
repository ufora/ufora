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

#include <limits>

// The following helper methods are designed to help in avoiding overflow
// They return 'false' if overflow will occur, and 'true' otherwise.
template <class T> class Overflow
	{
	public:

		static bool checkAdd(T left, T right)
			{
			if(left > 0 && right > 0)
				return std::numeric_limits<T>::max() - left > right;
			if(left < 0 && right < 0)
				return std::numeric_limits<T>::min() - left < right;
			return true;
			}

		static T safeAdd(T left, T right)
			{
			lassert(checkAdd(left, right));
			return left + right;
			}

		static bool checkMul(T left, T right)
			{
			return std::numeric_limits<T>::max() / left > right;
			}

		static T safeMul(T left, T right)
			{
			lassert(checkMul(left, right));
			return left * right;
			}
	};

