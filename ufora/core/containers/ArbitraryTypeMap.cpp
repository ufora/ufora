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
#include "ArbitraryTypeMap.hpp"

ArbitraryTypeMap::~ArbitraryTypeMap()
	{
	boost::mutex::scoped_lock lock(mFunctionsMutex);

	for (auto it = mInstances.begin(); it != mInstances.end(); ++it)
		mDestructors[it->first](it->second);
	}

ArbitraryTypeMap::ArbitraryTypeMap(const ArbitraryTypeMap& in)
	{
	boost::mutex::scoped_lock lock(mFunctionsMutex);
	
	for (auto it = in.mInstances.begin(); it != in.mInstances.end(); ++it)
		mInstances[it->first] = mDuplicators[it->first](it->second);
	}

ArbitraryTypeMap& ArbitraryTypeMap::operator=(const ArbitraryTypeMap& in)
	{
	boost::mutex::scoped_lock lock(mFunctionsMutex);
	
	for (auto it = mInstances.begin(); it != mInstances.end(); ++it)
		mDestructors[it->first](it->second);
	
	mInstances.clear();

	for (auto it = in.mInstances.begin(); it != in.mInstances.end(); ++it)
		mInstances[it->first] = mDuplicators[it->first](it->second);

	return *this;
	}


boost::mutex ArbitraryTypeMap::mFunctionsMutex;

boost::unordered_map<void*, boost::function1<void, void*> > ArbitraryTypeMap::mDestructors;

boost::unordered_map<void*, boost::function1<void*, void*> > ArbitraryTypeMap::mDuplicators;

