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

#include "lassert.hpp"

namespace Ufora {

template<class T, class F>
auto min(const T& inContainer, const F& func) -> decltype(*inContainer.begin())
	{
	lassert(inContainer.size());

	auto minArg = *inContainer.begin();

	auto minVal = func(minArg);

	auto it = inContainer.begin();
	it++;

	auto it_end = inContainer.end();

	while (it != it_end)
		{
		auto minCandidate = func(*it);

		if (minCandidate < minVal)
			{
			minVal = minCandidate;
			minArg = *it;
			}

		++it;
		}

	return minArg;
	}

}
