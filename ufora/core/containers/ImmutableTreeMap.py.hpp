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
#include "ImmutableTreeVector.py.hpp"
#include "ImmutableTreeSet.hppml"
#include "ImmutableTreeMap.hppml"
#include "../IFF.hpp"
#include "../python/ExposeAsClass.hpp"
#include "../cppml/CPPMLThreadSafety.hppml"


template<class T>
class PythonWrapper;

template<class T1, class T2>
class PythonWrapper<ImmutableTreeMap<T1, T2> > {
public:
		class IndexError{};

		static uword_t size(const ImmutableTreeMap<T1, T2>& inMap)
			{
			return inMap.size();
			}

		static boost::python::object getItem(
							ImmutableTreeMap<T1, T2>& treeMap,
							T1 key
							)
			{
			if (treeMap.contains(key))
				return boost::python::object(*treeMap[key]);
			return boost::python::object();
			}

		static bool contains(
						ImmutableTreeMap<T1, T2>& treeMap,
						T1 key
						)
			{
			return treeMap.contains(key);
			}

		static ImmutableTreeMap<T1, T2> addTuple(	ImmutableTreeMap<T1, T2>& lhs, 
													boost::python::object o
													)
			{
			boost::python::extract<ImmutableTreeMap<T1, T2> > e(o);
			if (e.check())
				return lhs + e();

			boost::python::extract<T1> t1(o[0]);
			boost::python::extract<T2> t2(o[1]);

			lassert_dump(t1.check() && t2.check(), 
				"Only pairs of (" << 
					Ufora::debug::StackTrace::demangle(typeid(T1).name()) << ", " <<
					Ufora::debug::StackTrace::demangle(typeid(T2).name()) << ")" <<
					" or other instances of its own type may be added to " <<
					Ufora::debug::StackTrace::demangle(typeid(ImmutableTreeMap<T1, T2>).name())
				);

			return lhs + t1() + t2();
			}

		static boost::python::class_<ImmutableTreeMap<T1, T2> > 
							exportPythonInterface(const std::string& inTypename)
			{
			using namespace boost::python;

			return class_<ImmutableTreeMap<T1, T2> >(
					("ImmutableTreeMap" + inTypename).c_str(), init<>())
				.def("__len__", &size)
				.add_property("keys", &ImmutableTreeMap<T1, T2>::keys)
				.add_property("size", &size)
				.def("__getitem__", getItem)
				.def("__add__", addTuple)
				.def("contains", contains)
				;
			}
};


