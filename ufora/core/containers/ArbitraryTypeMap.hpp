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

#include <typeinfo>
#include <boost/unordered_map.hpp>
#include <boost/thread.hpp>
#include <boost/bind.hpp>

class ArbitraryTypeMap {
public:
	ArbitraryTypeMap()
		{
		}

	~ArbitraryTypeMap();

	ArbitraryTypeMap(const ArbitraryTypeMap& in);

	ArbitraryTypeMap& operator=(const ArbitraryTypeMap& in);

	size_t size() const
		{
		return mInstances.size();
		}

	template<class T>
	T& get()
		{
		static bool isInitialized = false;

		void* tname = (void*)typeid(T).name();

		if (!isInitialized)
			{
			boost::mutex::scoped_lock lock(mFunctionsMutex);

			mDestructors[tname] = boost::bind(&destroy<T>, boost::arg<1>());

			mDuplicators[tname] = boost::bind(&duplicate<T>, boost::arg<1>());
			}

		if (mInstances.find(tname) == mInstances.end())
			mInstances[tname] = (void*)new T();
			
		return *(T*)mInstances[tname];
		}

	template<class T>
	void erase()
		{
		void* tname = (void*)typeid(T).name();

		auto it = mInstances.find(tname);

		if (it == mInstances.end())
			return;

		void* value = it->second;
		mInstances.erase(it);

		boost::mutex::scoped_lock lock(mFunctionsMutex);
		mDestructors[tname](value);
		}

	void clear()
		{
		*this = ArbitraryTypeMap();
		}

private:
	template<class T>
	static void* duplicate(void* inValue)
		{
		return (void*)new T(*(T*)inValue);
		}

	template<class T>
	static void destroy(void* inValue)
		{
		((T*)inValue)->~T();
		}

	boost::unordered_map<void*, void*> mInstances;

	static boost::mutex mFunctionsMutex;

	static boost::unordered_map<void*, boost::function1<void, void*> > mDestructors;

	static boost::unordered_map<void*, boost::function1<void*, void*> > mDuplicators;
};
