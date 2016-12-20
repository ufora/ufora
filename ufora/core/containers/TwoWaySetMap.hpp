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

#include <map>
#include <set>
#include <stdint.h>
#include "../lassert.hpp"

template<class key_type, class value_type, class key_compare = std::less<key_type>, class value_compare = std::less<value_type> >
class TwoWaySetMap {
public:
		typedef std::map<key_type, std::set<value_type, value_compare>, key_compare> key_valueset_map;
		typedef std::map<value_type, std::set<key_type, key_compare>, value_compare> value_keyset_map;

		TwoWaySetMap() {}
		TwoWaySetMap(const TwoWaySetMap& in) : mValuesToKeys(in.mValuesToKeys), mKeysToValues(in.mKeysToValues) {}
		TwoWaySetMap& operator=(const TwoWaySetMap& in)
			{
			mValuesToKeys = in.mValuesToKeys;
			mKeysToValues = in.mKeysToValues;
			return *this;
			}

		uint32_t keyCount(void) const { return mKeysToValues.size(); }
		uint32_t valueCount(void) const { return mValuesToKeys.size(); }

		bool	contains(const key_type& key, const value_type& value) const
			{
			return getValues(key).find(value) != getValues(key).end();
			}

		const std::set<value_type, value_compare>& getValues(const key_type& inKey) const
			{
			if (mKeysToValues.find(inKey) == mKeysToValues.end())
				return mEmptyValues;
			return mKeysToValues.find(inKey)->second;
			}
		const std::set<key_type, key_compare>& getKeys(const value_type& inValue) const
			{
			if (mValuesToKeys.find(inValue) == mValuesToKeys.end())
				return mEmptyKeys;
			return mValuesToKeys.find(inValue)->second;
			}
		void insert(const std::set<key_type, key_compare>& inKey, const value_type& inValue)
			{
			for (typename std::set<key_type, key_compare>::const_iterator it = inKey.begin(); it != inKey.end();++it)
				insert(*it, inValue);
			}
		void drop(const std::set<key_type, key_compare>& inKey, const value_type& inValue)
			{
			for (typename std::set<key_type, key_compare>::const_iterator it = inKey.begin(); it != inKey.end();++it)
				drop(*it, inValue);
			}
		void update(const key_type& inKey, const std::set<value_type, value_compare>& inValues)
			{
				{
				std::set<value_type, value_compare> curValues(getValues(inKey));
				for (typename std::set<value_type, value_compare>::const_iterator it = curValues.begin(); it != curValues.end(); ++it)
					if (inValues.find(*it) == inValues.end())
						drop(inKey, *it);
				}

			insert(inKey, inValues);
			}
		void insert(const key_type& inKey, const std::set<value_type, value_compare>& inValue)
			{
			for (typename std::set<value_type, value_compare>::const_iterator it = inValue.begin(); it != inValue.end();++it)
				insert(inKey, *it);
			}
		void insert(const std::set<key_type, key_compare>& inKeys, const std::set<value_type, value_compare>& inValues)
			{
			for (typename std::set<value_type, value_compare>::const_iterator it = inValues.begin(); it != inValues.end();++it)
				insert(inKeys, *it);
			}

		template<class iterator_type>
		void insert(const key_type& inKey, iterator_type first, iterator_type second)
			{
			while(first != second)
				insert(inKey, *first++);
			}
		void drop(const key_type& inKey, const std::set<value_type, value_compare>& inValue)
			{
			for (typename std::set<value_type, value_compare>::const_iterator it = inValue.begin(); it != inValue.end();++it)
				drop(inKey, *it);
			}
		void dropKey(const key_type& inKey)
			{
			std::set<value_type, value_compare> vals(getValues(inKey));
			for (typename std::set<value_type, value_compare>::iterator it = vals.begin(); it != vals.end();++it)
				drop(inKey, *it);
			}
		void dropValue(const value_type& inVal)
			{
			std::set<key_type, key_compare> keys(getKeys(inVal));
			for (typename std::set<key_type, key_compare>::iterator it = keys.begin(); it != keys.end(); ++it)
				drop(*it, inVal);
			}
		void insert(const key_type& inKey, const value_type& inValue)
			{
			mKeysToValues[inKey].insert(inValue);
			mValuesToKeys[inValue].insert(inKey);
			}
		void drop(const key_type& inKey, const value_type& inValue)
			{
			if (!hasKey(inKey))
				return;

			auto& values = mKeysToValues[inKey];

			if (values.find(inValue) == values.end())
				return;

			values.erase(inValue);
			mValuesToKeys[inValue].erase(inKey);

			if (values.size() == 0)
				mKeysToValues.erase(inKey);

			if (mValuesToKeys[inValue].size() == 0)
				mValuesToKeys.erase(inValue);
			}
		const key_valueset_map& getKeysToValues(void) const
			{
			return mKeysToValues;
			}
		const value_keyset_map& getValuesToKeys(void) const
			{
			return mValuesToKeys;
			}
		const key_type& lowestKey(void) const
			{
			lassert(keyCount());
			return mKeysToValues.begin()->first;
			}
		const value_type& lowestValue(void) const
			{
			lassert(keyCount());
			return mValuesToKeys.begin()->first;
			}
		const key_type& highestKey(void) const
			{
			lassert(keyCount());
			return mKeysToValues.rbegin()->first;
			}
		const value_type& highestValue(void) const
			{
			lassert(keyCount());
			return mValuesToKeys.rbegin()->first;
			}
		bool hasKey(const key_type& inKey) const
			{
			return mKeysToValues.find(inKey) != mKeysToValues.end();
			}
		bool hasValue(const value_type& inVal) const
			{
			return mValuesToKeys.find(inVal) != mValuesToKeys.end();
			}

		template<class storage_type>
		void	serialize(storage_type& s) const
			{
			s.serialize(mKeysToValues);
			s.serialize(mValuesToKeys);
			}

		template<class storage_type>
		void	deserialize(storage_type& s)
			{
			s.deserialize(mKeysToValues);
			s.deserialize(mValuesToKeys);
			}
private:
		std::set<value_type, value_compare> 	mEmptyValues;
		std::set<key_type, key_compare> 		mEmptyKeys;

		key_valueset_map mKeysToValues;
		value_keyset_map mValuesToKeys;
};

template<class T, class storage_type>
class Serializer;

template<class T, class storage_type>
class Deserializer;

template<class key_type, class value_type, class key_compare_type,
											class value_compare_type, class storage_type>
class Serializer<
	TwoWaySetMap<key_type, value_type, key_compare_type, value_compare_type>,
	storage_type
	> {
public:
		static void serialize(
				storage_type& s,
				const TwoWaySetMap<key_type, value_type, key_compare_type, value_compare_type>& in
				)
			{
			in.serialize(s);
			}
};
template<class key_type, class value_type, class key_compare_type,
											class value_compare_type, class storage_type>
class Deserializer<
	TwoWaySetMap<key_type, value_type, key_compare_type, value_compare_type>,
	storage_type
	> {
public:
		static void deserialize(
					storage_type& s,
					TwoWaySetMap<key_type, value_type, key_compare_type, value_compare_type>& out
					)
			{
			out.deserialize(s);
			}
};

//given a graph, compute the minimum set of nodes such that all possible loops through the graph pass through at least one node
//pruneRootNodes determines whether nodes with no entrypoints should be left in (false)
template<class T, class compare>
void minimumGraphCovering(TwoWaySetMap<T, T, compare, compare> tree, std::set<T, compare>& out, const std::set<T,compare>& required, bool pruneRootNodes)
	{
	using namespace std;

	typedef TwoWaySetMap<T, T, compare, compare> 		map_type;
	typename map_type::key_valueset_map 				keys = tree.getKeysToValues();

	out = required;

	for (typename map_type::key_valueset_map::iterator it = keys.begin(), it_end = keys.end(); it != it_end; ++it)
		{
		T t = it->first;

		if (required.find(t) == required.end())
			{
			if (tree.getValues(t).find(t) == tree.getValues(t).end() && (pruneRootNodes || tree.getKeys(t).size()))
				{
				set<T, compare> down = tree.getValues(t);
				set<T, compare> up = tree.getKeys(t);
				tree.drop(up, t);
				tree.drop(t, down);
				for (auto t2: up)
					tree.insert(t2, down);
				}
			else
				out.insert(t);
			}
		}
	}
template<class T, class compare>
void minimumGraphCovering(TwoWaySetMap<T, T, compare, compare> tree, std::set<T, compare>& out, const std::set<T,compare>& required, bool pruneRootNodes, const std::vector<T>& removalOrder)
	{
	using namespace std;

	typedef TwoWaySetMap<T, T, compare, compare> 		map_type;
	typename map_type::key_valueset_map 				keys = tree.getKeysToValues();

	out = required;

	for (auto t: removalOrder)
		{
		if (required.find(t) == required.end())
			{
			if (tree.getValues(t).find(t) == tree.getValues(t).end() && (pruneRootNodes || tree.getKeys(t).size()))
				{
				set<T, compare> down = tree.getValues(t);
				set<T, compare> up = tree.getKeys(t);
				tree.drop(up, t);
				tree.drop(t, down);
				for (typename set<T>::iterator it2 = up.begin(), it_end2 = up.end(); it2 != it_end2; ++it2)
					tree.insert(*it2, down);
				}
			else
				out.insert(t);
			}
		}
	}
template<class T, class compare>
void minimumGraphCovering(const TwoWaySetMap<T, T, compare, compare>& tree, std::set<T, compare>& out, bool pruneRootNodes)
	{
	minimumGraphCovering(tree, out, std::set<T, compare>(), pruneRootNodes);
	}
//given a graph, compute the implied transitive closure if we remove a bunch of nodes.
//that is, if A->B and B->C and we remove "B", write A->C instead.
template<class T, class compare>
void graphRestriction(TwoWaySetMap<T, T, compare, compare> &tree, const std::set<T, compare>& toRemove)
	{
	using namespace std;

	for (auto t: toRemove)
		{
		set<T> down = tree.getValues(t);
		set<T> up = tree.getKeys(t);
		tree.drop(up, t);
		tree.drop(t, down);
		for (auto t2: up)
			tree.insert(t2, down);
		}
	}
