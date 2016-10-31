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

#include <stdint.h>
#include <boost/python.hpp>
#include <boost/python/slice.hpp>
#include <string>
#include "../debug/StackTrace.hpp"
#include "../python/utilities.hpp"
#include "MapWithIndex.hpp"
#include <boost/shared_ptr.hpp>

template<class T>
class PythonWrapper;

template<class key_type, class value_type>
class PythonWrapper<MapWithIndex<key_type, value_type> > {
public:
		typedef MapWithIndex<key_type, value_type>  map_type;

		static map_type* newImmutableFromList(boost::python::object o)
			{
			std::unique_ptr<map_type> tr(new map_type());

			for (int32_t k = 0 ;k < len(o);k++)
				{
				tr->set(
					boost::python::extract<key_type>(o[k][0]),
					boost::python::extract<value_type>(o[k][1])
					);
				}

			return tr.release();
			}
		static boost::python::object getKeys(map_type& m, const key_type& inKey)
			{
			boost::python::list tr;

			auto keySet(m.getKeys(inKey));
			for (auto it = keySet.begin(), it_end = keySet.end(); it != it_end; ++it)
				tr.append(*it);

			return tr;
			}

		template<class m_type, class k_type>
		static boost::python::object nextIterator(m_type& m, const k_type& inKey)
			{
			//it->first will be >= inKey
			auto it = m.lower_bound(inKey);

			if (it == m.end())
				return boost::python::object();

			if (inKey < it->first)
				return boost::python::object(it->first);

			++it;
			if (it == m.end())
				return boost::python::object();

			return boost::python::object(it->first);
			}

		template<class m_type, class k_type>
		static boost::python::object prevIterator(m_type& m, const k_type& inKey)
			{
			if (!m.size())
				return boost::python::object();

			//it->first will be >= inKey
			auto it = m.lower_bound(inKey);

			if (it == m.end())
				{
				it--;
				return boost::python::object(it->first);
				}

			//we found it. decrement
			if (it != m.begin())
				{
				it--;
				return boost::python::object(it->first);
				}
			else
				return boost::python::object();
			}

		static boost::python::object nextKey(map_type& m, const key_type& inKey)
			{
			return nextIterator(m.getKeyToValue(), inKey);
			}
		static boost::python::object nextValue(map_type& m, const value_type& inValue)
			{
			return nextIterator(m.getValueToKeys(), inValue);
			}

		static boost::python::object prevKey(map_type& m, const key_type& inKey)
			{
			return prevIterator(m.getKeyToValue(), inKey);
			}
		static boost::python::object prevValue(map_type& m, const value_type& inValue)
			{
			return prevIterator(m.getValueToKeys(), inValue);
			}

		static boost::python::class_<map_type, boost::shared_ptr<map_type> > exportPythonInterface(const std::string& inTypename)
			{
			using namespace Ufora::python;
			using namespace boost::python;

			return class_<map_type, boost::shared_ptr<map_type> >(
					(inTypename).c_str(), init<>())
				.def("size", &map_type::size)
				.def("__len__", &map_type::size)
				.def("keyCount", &map_type::keyCount)
				.def("valueCount", &map_type::valueCount)
				.def("hasKey", &map_type::hasKey)
				.def("hasValue", &map_type::hasValue)
				.def("getValue", &map_type::getValue)
				.def("drop", &map_type::drop)
				.def("set", &map_type::set)
				.def("__setitem__", &map_type::set)
				.def("insert", &map_type::insert)
				.def("lowestKey", &map_type::lowestKey,
						return_value_policy<copy_const_reference>()
						)
				.def("nextKey", &nextKey)
				.def("prevKey", &prevKey)
				.def("lowestValue", &map_type::lowestValue,
						return_value_policy<copy_const_reference>()
						)
				.def("nextValue", &nextValue)
				.def("prevValue", &prevValue)
				.def("highestKey", &map_type::highestKey,
						return_value_policy<copy_const_reference>()
						)
				.def("highestValue", &map_type::highestValue,
						return_value_policy<copy_const_reference>()
						)
				.def("getKeys", &getKeys)
				;
			}
};


