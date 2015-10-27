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
#include <string>
#include "../debug/StackTrace.hpp"
#include "../containers/ImmutableTreeVector.hppml"
#include "../math/Nullable.hpp"
#include <vector>
#include "utilities.hpp"
#include "VectorWrapper.hpp"

namespace Ufora {
namespace python {

template<class T>
class extractCPPMLTupleMember {
public:
	T operator()(boost::python::object in)
	{
	return boost::python::extract<T>(in)();
	}
};

template<class T>
class extractCPPMLTupleMember<Nullable<T> > {
public:
	Nullable<T> operator()(boost::python::object in)
		{
		if (in == boost::python::object())
			return null();
		return null() << boost::python::extract<T>(in)();
		}
};

template<class T>
class extractCPPMLTupleMember<ImmutableTreeVector<T> > {
public:
	ImmutableTreeVector<T> operator()(boost::python::object in)
		{
		boost::python::extract<ImmutableTreeVector<T>> extractor(in);

		if (extractor.check())
			return extractor();

		ImmutableTreeVector<T> res;

		bool failed = false;

		try {
			boost::python::object it = in.attr("__iter__")();
			
			while(true)
				{
				boost::python::object n = it.attr("next")();

				boost::python::extract<T> e(n);

				if (e.check())
					res = res + e();
				else
					{
					failed = true;
					break;
					}
				}
			}
		catch(...)
			{
			PyErr_Clear();
			}

		if (failed)
			throw std::logic_error(
				"One or more arguments couldn't be converted to " + 
					Ufora::debug::StackTrace::demangle(typeid(T).name())
				);
		
		return res;
		}
};

template<class T>
class CPPMLHeldAsValuePolicy {
public:
		typedef boost::python::class_<T> 	boost_python_class;
		typedef T 							python_held_type;
		typedef T							wrapped_type;

		static wrapped_type& 	extractWrappedFromHeld(python_held_type& in)
			{
			return in;
			}
		static const python_held_type&	embedWrappedInHeld(const wrapped_type& wrapped)
			{
			return wrapped;
			}
};

template<class T>
class CPPMLHeldAsSharedPtrPolicy {
public:
		typedef boost::python::class_<boost::shared_ptr<T> > boost_python_class;
		typedef boost::shared_ptr<T> python_held_type;
		typedef T wrapped_type;

		static wrapped_type& 	extractWrappedFromHeld(python_held_type& in)
			{
			return *in;
			}
		static python_held_type	embedWrappedInHeld(const wrapped_type& wrapped)
			{
			return boost::shared_ptr<T>(new wrapped_type(wrapped));
			}
};

template<class T>
class CPPMLWrapperPolicy {
public:
		typedef CPPMLHeldAsValuePolicy<T> result_type;
};

template<class T1, class wrapper_policy, class T2>
class CPPMLClassMembers;

template<class T, class wrapper_policy, class kind>
class CPPMLClassWrapper;

template<class T, class wrapper_policy>
class CPPMLClassMembers<T, wrapper_policy, CPPML::Null> {
public:
		static void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy, class T1, class T2>
class CPPMLClassMembers<T, wrapper_policy, CPPML::Chain<T1, T2> > {
public:
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			m1.addMembers(inClass, readonly);
			m2.addMembers(inClass, readonly);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			m1.finish(inClass);
			m2.finish(inClass);
			}
		CPPMLClassMembers<T, wrapper_policy, T1> m1;
		CPPMLClassMembers<T, wrapper_policy, T2> m2;
};


template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in, bool isClass>
class CPPMLClassMembersDependent;



template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembersDependent<T, wrapper_policy, tuple_type_in, member_type_in, accessor_in, member_index_in, false> {
public:
		static member_type_in get(typename wrapper_policy::python_held_type& self)
			{
			return accessor_in::get(wrapper_policy::extractWrappedFromHeld(self));
			}
		static void set(typename wrapper_policy::python_held_type& self, boost::python::object in)
			{
			accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)) = boost::python::extract<member_type_in>(in)();
			}
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			if (readonly)
				inClass.add_property(std::string(accessor_in::name()).c_str(), &get);
				else
				inClass.add_property(std::string(accessor_in::name()).c_str(), &get, &set);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};


template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembersDependent<T, wrapper_policy, tuple_type_in, member_type_in, accessor_in, member_index_in, true> {
public:
		static member_type_in& get(typename wrapper_policy::python_held_type& self)
			{
			return accessor_in::get(wrapper_policy::extractWrappedFromHeld(self));
			}
		static void set(typename wrapper_policy::python_held_type& self, boost::python::object in)
			{
			accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)) = boost::python::extract<member_type_in>(in)();
			}
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			if (readonly)
				inClass.add_property(std::string(accessor_in::name()).c_str(), 
						boost::python::make_function(&get, boost::python::return_internal_reference<>()));
				else
				inClass.add_property(std::string(accessor_in::name()).c_str(), 
						boost::python::make_function(&get, boost::python::return_internal_reference<>()), &set);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};


template<class T, class wrapper_policy, class tuple_type_in, class member_element_type, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembersDependent<T, wrapper_policy, tuple_type_in, vector<member_element_type>, accessor_in, member_index_in, true> {
public:
		typedef VectorWrapper<member_element_type> vec_type;

		static vec_type* get(typename wrapper_policy::python_held_type& self)
			{
			return new vec_type(accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)));
			}
		static void set(typename wrapper_policy::python_held_type& self, boost::python::object o)
			{
			boost::python::extract<vec_type> e(o);
			if (e.check())
				accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)) = (e()).mVector[0];
				else
				Ufora::python::toCPP(o, accessor_in::get(self));
			}
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			PythonWrapper<vec_type>::defineFactory("");

			if (readonly)
				inClass.add_property(std::string(accessor_in::name()).c_str(), 
					boost::python::make_function(&get, 
						boost::python::with_custodian_and_ward_postcall<0,1, boost::python::return_value_policy<boost::python::manage_new_object> >()));
				else
				inClass.add_property(std::string(accessor_in::name()).c_str(), 
					boost::python::make_function(&get, 
						boost::python::with_custodian_and_ward_postcall<0,1, boost::python::return_value_policy<boost::python::manage_new_object> >()), &set);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};


template<class T, class wrapper_policy, class whatever>
class CPPMLAddTupleInit {
public:
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Null> {
public:
		static typename wrapper_policy::python_held_type* func(void)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(T())
				);
			}

		template<class U>
		static U constructAlternative(void)
			{
			return U(T());
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy, class A1>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Null> > {
public:
		static typename wrapper_policy::python_held_type* func(boost::python::object in1)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(extractCPPMLTupleMember<typename A1::member_type>()(in1))
					)
				);
			}

		template<class U>
		static U constructAlternative(boost::python::object in1)
			{
			return U(T(extractCPPMLTupleMember<typename A1::member_type>()(in1)));
			}

		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy, class A1, class A2>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Null> > > {
public:
		static typename wrapper_policy::python_held_type* func(boost::python::object in1, boost::python::object in2)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2)
						)
					)
				);
			}

		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy, class A1, class A2, class A3>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Chain<A3, CPPML::Null> > > > {
public:
		static typename wrapper_policy::python_held_type* func(boost::python::object in1, boost::python::object in2, boost::python::object in3)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3)
						)
					)
				);
			}

		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2, boost::python::object in3)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class A1, class A2, class A3, class A4>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Chain<A3, CPPML::Chain<A4, CPPML::Null> > > > > {
public:
		static typename wrapper_policy::python_held_type* func(boost::python::object in1, boost::python::object in2, boost::python::object in3, boost::python::object in4)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4)
						)
					)
				);
			}
		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2, boost::python::object in3, boost::python::object in4)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};
template<class T, class wrapper_policy, class A1, class A2, class A3, class A4, class A5>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Chain<A3, CPPML::Chain<A4, CPPML::Chain<A5, CPPML::Null> > > > > > {
public:
		static typename wrapper_policy::python_held_type* func(
								boost::python::object in1, 
								boost::python::object in2, 
								boost::python::object in3, 
								boost::python::object in4, 
								boost::python::object in5
								)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5)
						)
					)
				);
			}
		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2, boost::python::object in3, boost::python::object in4, boost::python::object in5)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class A1, class A2, class A3, class A4, class A5, class A6>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Chain<A3, CPPML::Chain<A4, CPPML::Chain<A5, CPPML::Chain<A6, CPPML::Null> > > > > > > {
public:
		static typename wrapper_policy::python_held_type* func(
								boost::python::object in1, 
								boost::python::object in2, 
								boost::python::object in3, 
								boost::python::object in4, 
								boost::python::object in5, 
								boost::python::object in6
								)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5),
						extractCPPMLTupleMember<typename A6::member_type>()(in6)
						)
					)
				);
			}
		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2, boost::python::object in3, boost::python::object in4, boost::python::object in5, boost::python::object in6)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5),
						extractCPPMLTupleMember<typename A6::member_type>()(in6)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class A1, class A2, class A3, class A4, class A5, class A6, class A7>
class CPPMLAddTupleInit<T, wrapper_policy, CPPML::Chain<A1, CPPML::Chain<A2, CPPML::Chain<A3, CPPML::Chain<A4, CPPML::Chain<A5, CPPML::Chain<A6, CPPML::Chain<A7, CPPML::Null> > > > > > > > {
public:
		static typename wrapper_policy::python_held_type* func(
								boost::python::object in1, 
								boost::python::object in2, 
								boost::python::object in3, 
								boost::python::object in4, 
								boost::python::object in5, 
								boost::python::object in6, 
								boost::python::object in7
								)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5),
						extractCPPMLTupleMember<typename A6::member_type>()(in6),
						extractCPPMLTupleMember<typename A7::member_type>()(in7)
						)
					)
				);
			}
		template<class U>
		static U constructAlternative(boost::python::object in1, boost::python::object in2, boost::python::object in3, boost::python::object in4, boost::python::object in5, boost::python::object in6, boost::python::object in7)
			{
			return U(
					T(
						extractCPPMLTupleMember<typename A1::member_type>()(in1),
						extractCPPMLTupleMember<typename A2::member_type>()(in2),
						extractCPPMLTupleMember<typename A3::member_type>()(in3),
						extractCPPMLTupleMember<typename A4::member_type>()(in4),
						extractCPPMLTupleMember<typename A5::member_type>()(in5),
						extractCPPMLTupleMember<typename A6::member_type>()(in6),
						extractCPPMLTupleMember<typename A7::member_type>()(in7)
						)
					);
			}
		void operator()(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.def("__init__", boost::python::make_constructor(func));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembers<T, wrapper_policy, CPPML::TupleMember<tuple_type_in, member_type_in, accessor_in, member_index_in>  > {
public:
		CPPMLClassMembersDependent<T, wrapper_policy, tuple_type_in, member_type_in, accessor_in, member_index_in, ExposeAsClass<member_type_in>::value> mDep;

		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			mDep.addMembers(inClass, readonly);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembers<T, wrapper_policy, CPPML::AlternativeCommonMember<tuple_type_in, member_type_in, accessor_in, member_index_in>  > {
public:
		CPPMLClassMembersDependent<T, wrapper_policy, tuple_type_in, member_type_in, accessor_in, member_index_in, ExposeAsClass<member_type_in>::value> mDep;

		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			mDep.addMembers(inClass, readonly);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class tuple_type_in, class member_type_in, class accessor_in, const int32_t member_index_in>
class CPPMLClassMembers<T, wrapper_policy, CPPML::TupleMember<tuple_type_in, Nullable<member_type_in>, accessor_in, member_index_in>  > {
public:
		static boost::python::object get(typename wrapper_policy::python_held_type& self)
			{
			if (accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)))
				return boost::python::object(*accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)));
				else
				return boost::python::object();
			}
		static void set(typename wrapper_policy::python_held_type& self, boost::python::object in)
			{
			boost::python::extract<member_type_in> e(in);
			if (e.check())
				accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)) = e();
				else
				accessor_in::get(wrapper_policy::extractWrappedFromHeld(self)) = Nullable<member_type_in>();
			}
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			if (readonly)
				inClass.add_property(std::string(accessor_in::name()).c_str(), &get);
				else
				inClass.add_property(std::string(accessor_in::name()).c_str(), &get, &set);
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			}
};

template<class T, class wrapper_policy, class self_type, class member_type_in, class accessor_in>
class CPPMLClassMembers<T, wrapper_policy, CPPML::Alternative<self_type, member_type_in, accessor_in> > {
public:
		static member_type_in& get(typename wrapper_policy::python_held_type& self)
			{
			return accessor_in::getNonconst(
				wrapper_policy::extractWrappedFromHeld(self), 
				true
				);
			}
		void addMembers(typename wrapper_policy::boost_python_class& inClass, bool readonly)
			{
			childType.addMembers(readonly);

			inClass.def(
					accessor_in::name(),
					&(CPPMLAddTupleInit<member_type_in, wrapper_policy, typename member_type_in::metadata>::template constructAlternative<T>)
					);
			inClass.def(("is" + std::string(accessor_in::name())).c_str(), &accessor_in::is);
			inClass.add_property(("as" + std::string(accessor_in::name())).c_str(), boost::python::make_function(&get, boost::python::return_internal_reference<>()));
			}
		void finish(typename wrapper_policy::boost_python_class& inClass)
			{
			inClass.staticmethod(accessor_in::name());
			}
		CPPMLClassWrapper<member_type_in,
			typename CPPMLWrapperPolicy<member_type_in>::result_type,
			typename member_type_in::kind
			> childType;
};


template<class T, class wrapper_policy, class kind>
class CPPMLClassWrapper {
public:
		CPPMLClassWrapper() :
				mClass(
					Ufora::debug::StackTrace::demangle(typeid(T).name()).c_str(),
					boost::python::init<typename wrapper_policy::python_held_type>()
					)
			{
			}
		CPPMLClassWrapper(string inClassName) :
				mClass(
					inClassName.c_str(),
					boost::python::init<typename wrapper_policy::python_held_type>()
					)
			{
			}
		static typename wrapper_policy::python_held_type* emptyInit(void)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(T())
				);
			}
		void addMembers(bool readonly)
			{
			mMembers.addMembers(mClass, readonly);
			mClass.def("__init__", boost::python::make_constructor(emptyInit));
			CPPMLAddTupleInit<T, wrapper_policy, typename T::metadata>()(mClass);
			}
		void finish(void)
			{
			mMembers.finish(mClass);
			}
//private:
		typename wrapper_policy::boost_python_class mClass;
		CPPMLClassMembers<T, wrapper_policy, typename T::metadata> mMembers;
};
template<class T, class wrapper_policy>
class CPPMLClassWrapper<T, wrapper_policy, CPPML::Kinds::alternative> {
public:
		CPPMLClassWrapper() :
					mClass(
						Ufora::debug::StackTrace::demangle(typeid(T).name()).c_str(),
						boost::python::init<typename wrapper_policy::python_held_type>()
						)
			{
			}
		CPPMLClassWrapper(string inClassname) :
					mClass(
						inClassname.c_str(),
						boost::python::init<typename wrapper_policy::python_held_type>()
						)
			{
			}
		static typename wrapper_policy::python_held_type* emptyInit(void)
			{
			return new typename wrapper_policy::python_held_type(
				wrapper_policy::embedWrappedInHeld(T())
				);
			}
		void addMembers(bool readonly)
			{
			mMembers.addMembers(mClass, readonly);
			mClass.def("__init__", boost::python::make_constructor(emptyInit));
			mClass.add_property("tag", &T::tagName);
			}
		void finish(void)
			{
			mMembers.finish(mClass);
			}
		typename wrapper_policy::boost_python_class mClass;
		CPPMLClassMembers<T, wrapper_policy, typename T::metadata>	mMembers;
};

template<class T>
class CPPMLWrapper {
		typedef typename CPPMLWrapperPolicy<T>::result_type wrapper_policy;
public:
		CPPMLWrapper(bool readonly = true)
			{
			using namespace boost::python;

			wrapper.addMembers(readonly);
			}
		CPPMLWrapper(string classname, bool readonly = true) : wrapper(classname)
			{
			using namespace boost::python;

			wrapper.addMembers(readonly);
			}
		~CPPMLWrapper()
			{
			wrapper.finish();
			}
		const typename wrapper_policy::boost_python_class& class_(void) const
			{
			return wrapper.mClass;
			}
		typename wrapper_policy::boost_python_class& class_(void)
			{
			return wrapper.mClass;
			}
private:
		CPPMLClassWrapper<T, wrapper_policy, typename T::kind> wrapper;
};

}
}

