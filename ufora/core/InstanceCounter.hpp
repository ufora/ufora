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

#include "AtomicOps.hpp"
#include "Clock.hpp"
#include "Logging.hpp"

template<class T>
class InstanceCounter {
public:
	InstanceCounter() : mDontIncludeInCounts(false)
		{
		AO_fetch_and_add_full(&mCounts, 1);

		LOG_DEBUG << "Create " 
			<< Ufora::debug::StackTrace::demangle(typeid(T).name()) 
			<< ". Total = " << totalCount();
		}
	virtual ~InstanceCounter()
		{
		if (!mDontIncludeInCounts)
			AO_fetch_and_add_full(&mCounts, -1);

		LOG_DEBUG << "Destroy " 
			<< Ufora::debug::StackTrace::demangle(typeid(T).name()) 
			<< ". Total = " << totalCount();
		}

	static unsigned long totalCount()
		{
		return AO_load(&mCounts);
		}

	void dontIncludeInCounts()
		{
		if (!mDontIncludeInCounts)
			AO_fetch_and_add_full(&mCounts, -1);

		mDontIncludeInCounts = true;
		}

private:
	static AO_t mCounts;

	bool mDontIncludeInCounts;
};

template<class T>
AO_t InstanceCounter<T>::mCounts;

