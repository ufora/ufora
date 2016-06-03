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

#include "../math/Nullable.hpp"
#include <boost/thread.hpp>
#include <map>

//a thread-safe map

template<class K, class V, class mutex_type = boost::mutex>
class ThreadSafeMap {
public:
	typedef typename mutex_type::scoped_lock scoped_lock_type;

	//get the value associated with K. returns null if its not
	//in the map.
	Nullable<V>	get(const K& in) const
		{
		scoped_lock_type lock(mMutex);

		if (mMap.find(in) != mMap.end())
			return null() << mMap.find(in)->second;
		return null();
		}

	//get the value associated with K. returns a default value constructed
	// by the provided factory if its not in the map.
	template<class factory_type>
	V getOrCreate(const K& in, const factory_type& inFactory)
		{
		scoped_lock_type lock(mMutex);

		if (mMap.find(in) == mMap.end())
			mMap[in] = inFactory();

		return mMap.find(in)->second;
		}

	//returns true if the map contains key 'in'
	bool contains(const K& in) const
		{
		scoped_lock_type lock(mMutex);

		return mMap.find(in) != mMap.end();
		}

	//set 'in' to value 'inV'
	void	set(const K& in, const V& inV)
		{
		set(in, null() << inV);
		}

	//set 'in' to value inV. if inV is null, remove it
	void	set(const K& in, const Nullable<V>& inV)
		{
		scoped_lock_type lock(mMutex);

		if (inV)
			mMap[in] = *inV;
			else
			mMap.erase(in);
		}

	//if 'in' has value 'inCurVal', update it and return true, otherwise return false
	bool testAndSet(const K& in, const Nullable<V>& inCurVal, const Nullable<V>& inUpdateVal)
		{
		scoped_lock_type lock(mMutex);

		auto curIt = mMap.find(in);

		if (!inCurVal && curIt != mMap.end())
			return false;

		if (inCurVal && (curIt == mMap.end() || curIt->second != *inCurVal))
			return false;

		if (inUpdateVal)
			mMap[in] = *inUpdateVal;
			else
			mMap.erase(in);

		return true;
		}

	size_t size() const
		{
		scoped_lock_type lock(mMutex);
		return mMap.size();
		}

	void getAll(std::map<K, V>& out) const
		{
		scoped_lock_type lock(mMutex);
		out = mMap;
		}

private:
	std::map<K, V> mMap;
	mutable mutex_type mMutex;
};

