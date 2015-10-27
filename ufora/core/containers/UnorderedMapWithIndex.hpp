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

#include <stdint.h>
#include "../lassert.hpp"
#include "../serialization/Serialization.fwd.hpp"
#include "../serialization/BoostContainerSerializers.hpp"

template<class key_type, class value_type>
class UnorderedMapWithIndex {
public:
		typedef boost::unordered_map<key_type, value_type> key_value_map;

		typedef boost::unordered_map<value_type, boost::unordered_set<key_type> > value_keyset_map;

		UnorderedMapWithIndex() {}
		UnorderedMapWithIndex(const UnorderedMapWithIndex& in) : mValueToKeys(in.mValueToKeys), mKeyToValue(in.mKeyToValue) {}
		UnorderedMapWithIndex& operator=(const UnorderedMapWithIndex& in)
			{
			mValueToKeys = in.mValueToKeys;
			mKeyToValue = in.mKeyToValue;
			return *this;
			}

		uint32_t size(void) const 
			{ 
			return keyCount(); 
			}
		
		uint32_t keyCount(void) const 
			{ 
			return mKeyToValue.size(); 
			}
		
		uint32_t valueCount(void) const 
			{
			return mValueToKeys.size(); 
			}

		bool hasKey(const key_type& inKey) const
			{
			return mKeyToValue.find(inKey) != mKeyToValue.end();
			}

		bool hasValue(const value_type& inValue) const
			{
			return mValueToKeys.find(inValue) != mValueToKeys.end();
			}

		const value_type getValue(const key_type& inKey) const
			{
			lassert(hasKey(inKey));

			return mKeyToValue.find(inKey)->second;
			}

		const boost::unordered_set<key_type>& getKeys(const value_type& inValue) const
			{
			if (mValueToKeys.find(inValue) == mValueToKeys.end())
				return mEmptyKeys;
			return mValueToKeys.find(inValue)->second;
			}

		void dropValue(const value_type& inValue)
			{
			while (hasValue(inValue))
				drop(*getKeys(inValue).begin());
			}

		void drop(key_type inKey)
			{
			lassert(hasKey(inKey));
			
			value_type value = getValue(inKey);

			mValueToKeys[value].erase(inKey);

			if (mValueToKeys[value].size() == 0)
				mValueToKeys.erase(value);

			mKeyToValue.erase(inKey);
			}

		void set(const key_type& inKey, const value_type& inValue)
			{
			if (hasKey(inKey))
				drop(inKey);
			insert(inKey, inValue);
			}

		void insert(const key_type& inKey, const value_type& inValue)
			{
			lassert(!hasKey(inKey));
			mKeyToValue[inKey] = inValue;
			mValueToKeys[inValue].insert(inKey);
			}

		const key_value_map& getKeyToValue(void) const
			{
			return mKeyToValue;
			}

		const value_keyset_map& getValueToKeys(void) const
			{
			return mValueToKeys;
			}
private:
		boost::unordered_set<key_type> mEmptyKeys;
		
		key_value_map mKeyToValue;

		value_keyset_map mValueToKeys;
};

template<class T1, class T2, class storage_type>
class Serializer<UnorderedMapWithIndex<T1, T2>, storage_type> {
public:
		static void serialize(storage_type& s, const UnorderedMapWithIndex<T1, T2>& o)
			{
			uint32_t sz = o.size();
			s.serialize(sz);

			for (auto it = o.getKeyToValue().begin(), it_end = o.getKeyToValue().end(); 
					it != it_end; ++it)
				{
				s.serialize(it->first);
				s.serialize(it->second);
				}
			}
};

template<class T1, class T2, class storage_type>
class Deserializer<UnorderedMapWithIndex<T1, T2>, storage_type> {
public:
		static void deserialize(storage_type& s, UnorderedMapWithIndex<T1, T2>& o)
			{
			o = UnorderedMapWithIndex<T1,T2>();
			uint32_t sz;
			s.deserialize(sz);

			for (uint32_t k = 0; k < sz; k++)
				{
				T1 key;
				T2 val;
				s.deserialize(key);
				s.deserialize(val);

				o.set(key,val);
				}
			}
};


