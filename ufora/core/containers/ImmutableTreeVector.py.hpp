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
#include "ImmutableTreeVector.hppml"
#include "ImmutableTreeSet.hppml"
#include "ImmutableTreeMap.hppml"
#include "../IFF.hpp"
#include "../python/ExposeAsClass.hpp"
#include "../cppml/CPPMLThreadSafety.hppml"


template<class T, bool isclass = Ufora::python::ExposeAsClass<T>::value >
class ImmutableTreeWrapperRetType;

template<class T>
class ImmutableTreeWrapperRetType<T,true> {
public:
		typedef const T& res_type;
};

template<class T>
class ImmutableTreeWrapperRetType<T,false> {
public:
		typedef T res_type;
};

template<class T>
class PythonWrapper;

template<class T>
class PythonWrapper<ImmutableTreeVector<T> > {
public:
		class IndexError{};

		static void indexError(IndexError arg)
			{
			PyErr_SetString(PyExc_IndexError, "Index out of range");
			}

		static ImmutableTreeVector<T>* newImmutableFromList(boost::python::object o)
			{
			ImmutableTreeVector<T> v;

			for (int32_t k = 0 ;k < len(o);k++)
				v = v + boost::python::extract<T>(o[k]);

			return new ImmutableTreeVector<T>(v);
			}
		static typename ImmutableTreeWrapperRetType<T>::res_type getVal(ImmutableTreeVector<T>& self, int32_t ix)
			{
			if (ix >= 0 && ix < self.size())
				return self[ix];

			throw IndexError();
			}
		static ImmutableTreeVector<T> addElement(ImmutableTreeVector<T>& self, typename ImmutableTreeWrapperRetType<T>::res_type other)
			{
			return self + other;
			}
		static ImmutableTreeVector<T> addElementReverse(ImmutableTreeVector<T>& self, typename ImmutableTreeWrapperRetType<T>::res_type other)
			{
			return other + self;
			}
		static ImmutableTreeVector<T> addTree(ImmutableTreeVector<T>& self, ImmutableTreeVector<T>& other)
			{
			return self + other;
			}
		static uint32_t size(ImmutableTreeVector<T>& in)
			{
			return in.size();
			}
		static ImmutableTreeVector<T> slice(ImmutableTreeVector<T>& in, boost::python::slice s)
			{
			int32_t start = boost::python::extract<int32_t>(s.start());
			if (start < 0)
				start = in.size() - start;

			int32_t stop = boost::python::extract<int32_t>(s.stop());
			if (stop < 0)
				stop = in.size() - stop;

			return in.slice(start, stop);
			}
		static long cmpTrees(ImmutableTreeVector<T>& inLeft, boost::python::object o)
			{
			boost::python::extract<ImmutableTreeVector<T> > extractor(o);
			if (extractor.check())
				return cppmlCmp(inLeft, extractor());
			return -1;
			}
		static boost::python::class_<ImmutableTreeVector<T> > exportPythonInterface(const std::string& inTypename)
			{
			using namespace Ufora::python;
			using namespace boost::python;

			boost::python::register_exception_translator<IndexError>(&indexError);

			return class_<ImmutableTreeVector<T> >(
					("ImmutableTreeVectorOf" + inTypename).c_str(), init<>())
				.def(init<T>())
				.def(init<vector<T> >())
				.def("__init__", make_constructor(&newImmutableFromList))
				.def("__len__", &size)
				.def("__getitem__", &getVal, typename IFF<ExposeAsClass<T>::value, return_internal_reference<>, default_call_policies>::res())
				.def("__getitem__", &slice)
				.def("__add__", &addElement)
				.def("__radd__", &addElementReverse)
				.def("__add__", &addTree)
				.def("__str__", prettyPrintString<ImmutableTreeVector<T> >)
				.def("__cmp__", cmpTrees)
				;
			}
};


template<class T>
ImmutableTreeVector<T> extractItvFromPythonList(boost::python::object o)
	{
	ImmutableTreeVector<T> tr;
	
	for (long k = 0; k < boost::python::len(o);k++)
		tr = tr + T(boost::python::extract<T>(o[k])());

	return tr;
	}


