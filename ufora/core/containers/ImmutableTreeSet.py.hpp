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
#include "ImmutableTreeVector.hppml"
#include "ImmutableTreeSet.hppml"
#include "ImmutableTreeMap.hppml"
#include "../IFF.hpp"
#include "../python/ExposeAsClass.hpp"
#include "../cppml/CPPMLThreadSafety.hppml"


template<class T>
class PythonWrapper;


template<class T>
class PythonWrapper<ImmutableTreeSet<T> > {
public:
		class IndexError{};

		static void indexError(IndexError arg)
			{
			PyErr_SetString(PyExc_IndexError, "Index out of range");
			}

		static ImmutableTreeSet<T>* newImmutableFromList(boost::python::object o)
			{
			ImmutableTreeSet<T> v;

			for (int32_t k = 0 ;k < len(o);k++)
				v = v + boost::python::extract<T>(o[k])();

			return new ImmutableTreeSet<T>(v);
			}
		static typename ImmutableTreeWrapperRetType<T>::res_type getVal(ImmutableTreeSet<T>& self, int32_t ix)
			{
			if (ix >= 0 && ix < self.size())
				return self[ix];

			throw IndexError();
			}
		static ImmutableTreeSet<T> addElement(ImmutableTreeSet<T>& self, typename ImmutableTreeWrapperRetType<T>::res_type other)
			{
			return self + other;
			}
		static ImmutableTreeSet<T> addTree(ImmutableTreeSet<T>& self, ImmutableTreeSet<T>& other)
			{
			return self + other;
			}
		static uint32_t size(ImmutableTreeSet<T>& in)
			{
			return in.size();
			}
		static uint32_t getHeight(ImmutableTreeSet<T>& in)
			{
			return in.height();
			}
		static uint32_t lowerBound(ImmutableTreeSet<T>& in, const T& r)
			{
			return in.lowerBound(r);
			}
		static ImmutableTreeSet<T> slice(ImmutableTreeSet<T>& in, boost::python::slice s)
			{
			int32_t start = boost::python::extract<int32_t>(s.start());
			if (start < 0)
				start = in.size() - start;

			int32_t stop = boost::python::extract<int32_t>(s.stop());
			if (stop < 0)
				stop = in.size() - stop;

			return in.slice(start, stop);
			}
		static uint32_t test(uint32_t m)
			{
			ImmutableTreeMap<uint32_t, uint32_t> x;

			x = x + (uint32_t)0 + (uint32_t)1;
			x = x + (uint32_t)1 + (uint32_t)1;

			for (uint32_t ix = 2; ix <= m; ix++)
				x = x + ix + ix; //(*x[ix-2] + *x[ix-1]);

			return x.height();
			}
		static uint32_t test2(uint32_t m)
			{
			ImmutableTreeVector<uint32_t> x;

			for (uint32_t ix = 0; ix <= m; ix++)
				x = x + ix;

			return x.height();
			}
		static uint32_t test3(uint32_t m)
			{
			ImmutableTreeSet<uint32_t> x;

			for (uint32_t ix = 0; ix <= m; ix++)
				x = x + ix;

			return x.height();
			}
		static uint32_t test4(uint32_t m)
			{
			ImmutableTreeSet<uint32_t> x;

			for (uint32_t ix = 0; ix <= m; ix++)
				x = x + (uint32_t)rand();

			return x.height();
			}
		static void test5(uint32_t m)
			{
			for (long k = 0; k < m; k++)
				{
				ImmutableTreeMap<uint32_t, uint32_t> x;

				for (uint32_t ix = 0; ix <= 10; ix++)
					x = x + (uint32_t)rand() + (uint32_t)0;
				}
			for (long k = 0; k < m; k++)
				{
				ImmutableTreeSet<uint32_t> x;

				for (uint32_t ix = 0; ix <= 10; ix++)
					x = x + (uint32_t)rand();
				}
			for (long k = 0; k < m; k++)
				{
				ImmutableTreeVector<uint32_t> x;
				x = x + (uint32_t)1;

				for (uint32_t ix = 0; ix <= 10; ix++)
					{
					uint32_t ix2 = (rand() / (float)RAND_MAX) * x.size();
					x = x.slice(0,ix2) + (uint32_t)0 + x.slice(ix2);
					}

				}
			}
		static void exportPythonInterface(const std::string& inTypename)
			{
			using namespace Ufora::python;
			using namespace boost::python;

			boost::python::register_exception_translator<IndexError>(&indexError);

			class_<ImmutableTreeSet<T> >(
					("ImmutableTreeSetOf" + inTypename).c_str(), init<>())
				.def(init<T>())
				.def(init<vector<T> >())
				.def("__init__", make_constructor(&newImmutableFromList))
				.def("__len__", &size)
				.def("__getitem__", &getVal, typename IFF<ExposeAsClass<T>::value, return_internal_reference<>, default_call_policies>::res())
				.def("__getitem__", &slice)
				.def("__add__", &addElement)
				.def("__radd__", &addElement)
				.def("__add__", &addTree)
				.def("lowerBound", &lowerBound)
				.add_property("height", getHeight)
				;

			def("test", &test);
			def("test2", &test2);
			def("test3", &test3);
			def("test4", &test4);
			def("test5", &test5);
			}
};


