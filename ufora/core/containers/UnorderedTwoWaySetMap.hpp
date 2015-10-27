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

#include <boost/unordered_map.hpp>
#include <boost/unordered_set.hpp>
#include "../serialization/BoostContainerSerializers.hpp"
#include <set>
#include <stdint.h>
#include "../lassert.hpp"

template<class key_type, class value_type>
class UnorderedTwoWaySetMap {
public:
		typedef boost::unordered_map<key_type, boost::unordered_set<value_type> > key_valueset_map;
		typedef boost::unordered_map<value_type, boost::unordered_set<key_type> > value_keyset_map;

		UnorderedTwoWaySetMap() {}
		UnorderedTwoWaySetMap(const UnorderedTwoWaySetMap& in) : mValuesToKeys(in.mValuesToKeys), mKeysToValues(in.mKeysToValues) {}
		UnorderedTwoWaySetMap& operator=(const UnorderedTwoWaySetMap& in)
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
		
		const boost::unordered_set<value_type>& getValues(const key_type& inKey) const
			{
			if (mKeysToValues.find(inKey) == mKeysToValues.end())
				return mEmptyValues;
			return mKeysToValues.find(inKey)->second;
			}

		const boost::unordered_set<key_type>& getKeys(const value_type& inValue) const
			{
			if (mValuesToKeys.find(inValue) == mValuesToKeys.end())
				return mEmptyKeys;
			return mValuesToKeys.find(inValue)->second;
			}

		void insert(const boost::unordered_set<key_type>& inKey, const value_type& inValue)
			{
			for (auto it = inKey.begin(); it != inKey.end();++it)
				insert(*it, inValue);
			}

		void drop(const boost::unordered_set<key_type>& inKey, const value_type& inValue)
			{
			for (auto it = inKey.begin(); it != inKey.end();++it)
				drop(*it, inValue);
			}

		void update(const key_type& inKey, const boost::unordered_set<value_type>& inValues)
			{
				{
				boost::unordered_set<value_type> curValues(getValues(inKey));
				for (auto it = curValues.begin(); it != curValues.end(); ++it)
					if (inValues.find(*it) == inValues.end())
						drop(inKey, *it);
				}

			insert(inKey, inValues);
			}
		void insert(const key_type& inKey, const boost::unordered_set<value_type>& inValue)
			{
			for (auto it = inValue.begin(); it != inValue.end();++it)
				insert(inKey, *it);
			}
		void insert(const boost::unordered_set<key_type>& inKeys, const boost::unordered_set<value_type>& inValues)
			{
			for (auto it = inValues.begin(); it != inValues.end();++it)
				insert(inKeys, *it);
			}
		
		template<class iterator_type>
		void insert(const key_type& inKey, iterator_type first, iterator_type second)
			{
			while(first != second)
				insert(inKey, *first++);
			}
		void drop(const key_type& inKey, const boost::unordered_set<value_type>& inValue)
			{
			for (auto it = inValue.begin(); it != inValue.end();++it)
				drop(inKey, *it);
			}
		void dropKey(const key_type& inKey)
			{
			boost::unordered_set<value_type> vals(getValues(inKey));
			for (auto it = vals.begin(); it != vals.end();++it)
				drop(inKey, *it);
			}
		void dropValue(const value_type& inVal)
			{
			boost::unordered_set<key_type> keys(getKeys(inVal));
			for (auto it = keys.begin(); it != keys.end(); ++it)
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
			if (mKeysToValues[inKey].find(inValue) == mKeysToValues[inKey].end())
				return;

			mKeysToValues[inKey].erase(inValue);
			mValuesToKeys[inValue].erase(inKey);

			if (mKeysToValues[inKey].size() == 0)
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
		boost::unordered_set<value_type> 	mEmptyValues;
		boost::unordered_set<key_type> 		mEmptyKeys;

		key_valueset_map mKeysToValues;
		value_keyset_map mValuesToKeys;
};

template<class T, class storage_type>
class Serializer;

template<class T, class storage_type>
class Deserializer;

template<class key_type, class value_type, class storage_type>
class Serializer<
	UnorderedTwoWaySetMap<key_type, value_type>, 
	storage_type
	> {
public:
		static void serialize(
				storage_type& s, 
				const UnorderedTwoWaySetMap<key_type, value_type>& in
				)
			{
			in.serialize(s);
			}
};
template<class key_type, class value_type, class storage_type>
class Deserializer<
	UnorderedTwoWaySetMap<key_type, value_type>, 
	storage_type
	> {
public:
		static void deserialize(
					storage_type& s, 
					UnorderedTwoWaySetMap<key_type, value_type>& out
					)
			{
			out.deserialize(s);
			}
};


