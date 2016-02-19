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
#ifndef MapWithIndex_hpp_
#define MapWithIndex_hpp_

#include <map>
#include <set>
#include <stdint.h>
#include "../lassert.hpp"
#include "../math/Nullable.hpp"
#include "../serialization/Serialization.fwd.hpp"

template<class key_type, class value_type, class key_compare = std::less<key_type>, class value_compare = std::less<value_type> >
class MapWithIndex {
public:
		typedef std::map<key_type, value_type, key_compare> 							key_value_map;
		typedef std::map<value_type, std::set<key_type, key_compare>, value_compare> 	value_keyset_map;

		MapWithIndex() {}
		MapWithIndex(const MapWithIndex& in) : mValueToKeys(in.mValueToKeys), mKeyToValue(in.mKeyToValue) {}
		MapWithIndex& operator=(const MapWithIndex& in)
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

		Nullable<value_type> tryGetValue(const key_type& inKey) const
			{
			auto it = mKeyToValue.find(inKey);
			if (it == mKeyToValue.end())
				return null();
			else
				return null() << it->second;
			}

		const value_type getValue(const key_type& inKey) const
			{
			lassert(hasKey(inKey));

			return mKeyToValue.find(inKey)->second;
			}

		const std::set<key_type, key_compare>& getKeys(const value_type& inValue) const
			{
			if (mValueToKeys.find(inValue) == mValueToKeys.end())
				return mEmptyKeys;
			return mValueToKeys.find(inValue)->second;
			}

		void dropValue(const value_type& inValue)
			{
			for (auto key: getKeys(inValue))
				mKeyToValue.erase(key);

			mValueToKeys.erase(inValue);
			}

		void discard(key_type inKey)
			{
			if (hasKey(inKey))
				drop(inKey);
			}
		
		bool tryDrop(key_type inKey)
			{
			if (!hasKey(inKey))
				return false;
			drop(inKey);
			return true;
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

		bool tryInsert(const key_type& inKey, const value_type& inValue)
			{
			if(hasKey(inKey))
				return false;

			insert(inKey, inValue);
			return true;
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

		const key_type& lowestKey(void) const
			{
			lassert(keyCount());
			return mKeyToValue.begin()->first;
			}

		const value_type& lowestValue(void) const
			{
			lassert(keyCount());
			return mValueToKeys.begin()->first;
			}

		const key_type& highestKey(void) const
			{
			lassert(keyCount());
			return mKeyToValue.rbegin()->first;
			}

		const value_type& highestValue(void) const
			{
			lassert(keyCount());
			return mValueToKeys.rbegin()->first;
			}

		void clear()
			{
			mKeyToValue.clear();
			mValueToKeys.clear();
			}
private:
		std::set<key_type, key_compare>		 									mEmptyKeys;
		key_value_map 	 														mKeyToValue;
		value_keyset_map														mValueToKeys;
};

template<class T1, class T2, class cmp_type_1, class cmp_type_2, class storage_type>
class Serializer<MapWithIndex<T1, T2, cmp_type_1, cmp_type_2>, storage_type> {
public:
		static void serialize(storage_type& s, const MapWithIndex<T1, T2, cmp_type_1, cmp_type_2>& o)
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
template<class T1, class T2, class cmp_type_1, class cmp_type_2, class storage_type>
class Deserializer<MapWithIndex<T1, T2, cmp_type_1, cmp_type_2>, storage_type> {
public:
		static void deserialize(storage_type& s, MapWithIndex<T1, T2, cmp_type_1, cmp_type_2>& o)
			{
			o = MapWithIndex<T1,T2, cmp_type_1, cmp_type_2>();
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



#endif //MapWithIndex_hpp_

