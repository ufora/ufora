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
#ifndef core_Python_VectorWrapper_hpp_
#define core_Python_VectorWrapper_hpp_

#include "../IFF.hpp"
#include "../python/ExposeAsClass.hpp"
#include <stdint.h>
#include <boost/python.hpp>
#include <string>
#include "../debug/StackTrace.hpp"
#include <vector>
#include "utilities.hpp"


namespace Ufora {
namespace python {



template<class member_element_type>
class VectorConverter {
public:
		VectorConverter()
			{
			static bool converted = false;
			if (converted)
				return;
			converted = true;
			boost::python::converter::registry::push_back(&convertible, &construct, boost::python::type_id<vector<member_element_type> >());
			}
		static void* convertible(PyObject* obj_ptr)
			{
			using namespace boost::python;

			object obj(handle<>(borrowed(obj_ptr)));

			try {
				if (len(obj) == 0)
					return obj_ptr;
				for (int32_t k = 0 ;k < len(obj);k++)
					if (! boost::python::extract<member_element_type&>(obj[k]).check() )
						return 0;
				return obj_ptr;
				}
			catch(...)
				{
				return 0;
				}
			}

		static void construct(PyObject* obj_ptr, boost::python::converter::rvalue_from_python_stage1_data* data)
			{
			using namespace boost::python;

			// create storage space for our particular type of c++ object
			void* storage = ((boost::python::converter::rvalue_from_python_storage<vector<member_element_type> >*)data)->storage.bytes;
			  // in-place construct the new c++ object using the extracted data
			new (storage) vector<member_element_type>();

			vector<member_element_type> &v(((vector<member_element_type>*)storage)[0]);

			object obj(handle<>(borrowed(obj_ptr)));

			try {
				toCPP(obj, v);
				}
			catch(...)
				{
				}

			  // Stash the memory chunk pointer for later use by boost.python
			data->convertible = storage;
			}
};
template<class T, bool isConst, bool isclass = ExposeAsClass<T>::value >
class VectorWrapperRetType;;

template<class T>
class VectorWrapperRetType<T,false,true> {
public:
		typedef T& res_type;
};
template<class T>
class VectorWrapperRetType<T,false,false> {
public:
		typedef T res_type;
};
template<class T>
class VectorWrapperRetType<T,true,true> {
public:
		typedef const T& res_type;
};
template<class T>
class VectorWrapperRetType<T,true,false> {
public:
		typedef T res_type;
};

template<class T, bool readonly = false>
class VectorWrapper {
		VectorWrapper(const VectorWrapper& in) {}
public:
		VectorWrapper(vector<T>& in)
			{
			mVector = &in;
			mOwns = false;
			}
		static VectorWrapper* grabCopy(const vector<T>& in)
			{
			VectorWrapper* tr = new VectorWrapper(*(new vector<T>(in)));
			tr->mOwns = true;
			return tr;
			}
		VectorWrapper()
			{
			mVector = 0;
			mOwns = false;
			}
		~VectorWrapper()
			{
			if (mOwns && mVector)
				delete mVector;
			}
		int32_t len(void) const
			{
			if (!mVector)
				return 0;
			return mVector->size();
			}
		typename VectorWrapperRetType<T, false>::res_type get(int32_t ix)
			{
			lassert(ix >= 0 && ix < len());
			return (*mVector)[ix];
			}
		void set(int32_t ix, T& in)
			{
			lassert(ix >= 0 && ix < len());
			(*mVector)[ix] = in;
			}
		void append(T& in)
			{
			lassert(mVector);
			mVector->push_back(in);
			}

		vector<T> 		*mVector;
		bool			mOwns;
};
template<class T>
class VectorWrapper<T,true> {
		VectorWrapper(const VectorWrapper& in) {}
public:
		static VectorWrapper* grabCopy(const vector<T>& in)
			{
			VectorWrapper* tr = new VectorWrapper(*(new vector<T>(in)));
			tr->mOwns = true;
			return tr;
			}
		~VectorWrapper()
			{
			if (mOwns && mVector)
				delete mVector;
			}
		VectorWrapper(const vector<T>& in)
			{
			mOwns = false;
			mVector = &in;
			}
		int32_t len(void) const
			{
			if (!mVector)
				return 0;
			return mVector->size();
			}
		typename VectorWrapperRetType<T, true>::res_type get(int32_t ix)
			{
			lassert(ix >= 0 && ix < len());
			return (*mVector)[ix];
			}
		bool mOwns;
		const vector<T> 		*mVector;
};

} //namespace python
} //namespace Ufora

template<class T>
class PythonWrapper;



template<class T>
class PythonWrapper<Ufora::python::VectorWrapper<T, true> > {
public:
		static void defineFactory(std::string inFactoryName)
			{
			using namespace Ufora::python;
			using namespace boost::python;

			VectorConverter<T> c;

			class_<VectorWrapper<T,true>, boost::noncopyable>(
					("VectorOf" + std::string(Ufora::debug::StackTrace::demangle(typeid(T).name()))).c_str(), no_init)
				.def("__len__", &VectorWrapper<T,true>::len)
				.def("__getitem__", &VectorWrapper<T,true>::get, typename IFF<ExposeAsClass<T>::value, return_internal_reference<>, default_call_policies>::res());
			}
};

template<class T>
class PythonWrapper<Ufora::python::VectorWrapper<T, false> > {
public:
		static void defineFactory(std::string inFactoryName)
			{
			using namespace Ufora::python;
			using namespace boost::python;

			VectorConverter<T> c;

			class_<VectorWrapper<T, false>, boost::noncopyable>(
				("VectorOf" + std::string(Ufora::debug::StackTrace::demangle(typeid(T).name()))).c_str(), no_init)
				.def("__len__", &VectorWrapper<T,false>::len)
				.def("__getitem__", &VectorWrapper<T,false>::get, typename IFF<ExposeAsClass<T>::value, return_internal_reference<>, default_call_policies>::res())
				.def("__setitem__", &VectorWrapper<T,false>::set)
				.def("append", &VectorWrapper<T,false>::append);
			}
};
#endif

