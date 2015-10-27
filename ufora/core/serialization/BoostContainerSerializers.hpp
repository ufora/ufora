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

#include "Serialization.hpp"
#include <boost/unordered_map.hpp>
#include <boost/unordered_set.hpp>

template<class T, class storage_type>
class Serializer<boost::unordered_set<T>, storage_type> {
public:
		static void serialize(storage_type& s, const boost::unordered_set<T>& o)
			{
			uint32_t sz = o.size();
			s.serialize(sz);

			for (auto it = o.begin(), it_end = o.end(); it != it_end; ++it)
				s.serialize(*it);
			}
};

template<class T, class storage_type>
class Deserializer<boost::unordered_set<T>, storage_type> {
public:
		static void deserialize(storage_type& s, boost::unordered_set<T>& o)
			{
			o = boost::unordered_set<T>();
			uint32_t sz;
			s.deserialize(sz);

			for (int32_t k = 0; k < sz; k++)
				{
				T key;
				s.deserialize(key);
				o.insert(key);
				}
			}
};

template<class T1, class T2, class storage_type>
class Serializer<boost::unordered_map<T1, T2>, storage_type> {
public:
		static void serialize(storage_type& s, const boost::unordered_map<T1, T2>& o)
			{
			uint32_t sz = o.size();
			s.serialize(sz);

			for (typename boost::unordered_map<T1,T2>::const_iterator it = o.begin(), it_end = o.end(); it != it_end; ++it)
				{
				s.serialize(it->first);
				s.serialize(it->second);
				}
			}
};
template<class T1, class T2, class storage_type>
class Deserializer<boost::unordered_map<T1, T2>, storage_type> {
public:
		static void deserialize(storage_type& s, boost::unordered_map<T1, T2>& o)
			{
			o = boost::unordered_map<T1,T2>();
			uint32_t sz;
			s.deserialize(sz);

			for (int32_t k = 0; k < sz; k++)
				{
				T1 key;
				s.deserialize(key);
				s.deserialize(o[key]);
				}
			}
};


