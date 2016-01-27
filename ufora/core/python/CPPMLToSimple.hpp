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

#include "../Common.hppml"
#include "utilities.hpp"
#include "../math/Hash.hpp"
#include "../math/Nullable.hpp"
#include "../containers/ImmutableTreeVector.hppml"
#include "../containers/ImmutableTreeMap.hppml"
#include <boost/python.hpp>

template<class T, class directive>
class CPPMLToSimpleGivenDirective {};

template<class T, class kind, class metadata>
class CPPMLToSimpleGivenCppmlMetadata;

template<class T>
class CPPMLDirectiveIsCppmlType {};

template<class T>
class CPPMLDirectiveConvertToPython {};

template<class T>
class CPPMLDirectiveForType {
public:
	typedef CPPMLDirectiveIsCppmlType<T> result_type;
};


template<class T>
class CPPMLToSimple {
public:
	//type tag that determines how to convert this type
	typedef typename CPPMLDirectiveForType<T>::result_type directive_type;

	static boost::python::object toSimple(const T& in)
		{
		return CPPMLToSimpleGivenDirective<T, directive_type>::toSimple(in);
		}

	static void fromSimple(T& out, boost::python::object in)
		{
		CPPMLToSimpleGivenDirective<T, directive_type>::fromSimple(out, in);
		}
};

template<class T>
boost::python::object cppmlToSimplePythonRepresentation(const T& in)
	{
	return CPPMLToSimple<T>::toSimple(in);
	}

template<class T>
void cppmlFromSimplePythonRepresentation(T& out, const boost::python::object& in)
	{
	CPPMLToSimple<T>::fromSimple(out, in);
	}

template<class T>
T getFromSimplePythonRepresentation(boost::python::object in)
	{
	T tr;

	cppmlFromSimplePythonRepresentation(tr, in);

	return tr;
	}

template<class T>
class CPPMLToSimple<ImmutableTreeVector<T> > {
public:
	static boost::python::object toSimple(const ImmutableTreeVector<T>& in)
		{
		boost::python::object tr = boost::python::tuple();

		for (long k = 0; k < in.size();k++)
			tr = tr + boost::python::make_tuple(cppmlToSimplePythonRepresentation(in[k]));

		return tr;
		}

	static void fromSimple(ImmutableTreeVector<T>& out, boost::python::object in)
		{
		long length = boost::python::len(in);

		for (long k = 0; k < length; k++)
			{
			T res;

			CPPMLToSimple<T>::fromSimple(res, in[k]);

			out = out + res;
			}
		}
};

template<class T>
class CPPMLToSimple<Nullable<T> > {
public:
	static boost::python::object toSimple(const Nullable<T>& in)
		{
		if (!in)
			return boost::python::object();

		return CPPMLToSimple<T>::toSimple(*in);
		}

	static void fromSimple(Nullable<T>& out, boost::python::object in)
		{
		if (in.ptr() == Py_None)
			out = null();
		else
			{
			out = T();
			CPPMLToSimple<T>::fromSimple(*out, in);
			}
		}
};

template<class T1, class T2>
class CPPMLToSimple<ImmutableTreeMap<T1, T2> > {
public:
	static boost::python::object toSimple(const ImmutableTreeMap<T1, T2>& in)
		{
		boost::python::dict tr;

		for (long k = 0; k < in.size();k++)
			tr[cppmlToSimplePythonRepresentation(in.pairAtPosition(k).first)] = 
				cppmlToSimplePythonRepresentation(in.pairAtPosition(k).second);

		return tr;
		}

	static void fromSimple(ImmutableTreeMap<T1, T2>& out, boost::python::object in)
		{
		boost::python::dict d = boost::python::extract<boost::python::dict>(in)();

		boost::python::list keys = d.keys();

		long length = boost::python::len(keys);

		for (long k = 0; k < length; k++)
			{
			T1 key;
			T2 val;

			cppmlFromSimplePythonRepresentation(key, keys[k]);
			cppmlFromSimplePythonRepresentation(val, d[keys[k]]);

			out = out + make_pair(key,val);
			}
		}
};

//override for types that want to be converted directly to/from python
template<class T>
class CPPMLToSimpleGivenDirective<T, CPPMLDirectiveConvertToPython<T> > {
public:
	static boost::python::object toSimple(const T& in)
		{
		return boost::python::object(in);
		}
	static void fromSimple(T& out, boost::python::object in)
		{
		boost::python::extract<T> extract(in);
		lassert(extract.check());
		out = extract();
		}
};

#define macro_CPPMLToSimple_alreadySimple(T) \
template<> class CPPMLDirectiveForType<T> { public: typedef CPPMLDirectiveConvertToPython<T> result_type; };


macro_CPPMLToSimple_alreadySimple(std::string);
macro_CPPMLToSimple_alreadySimple(float);
macro_CPPMLToSimple_alreadySimple(double);
macro_CPPMLToSimple_alreadySimple(long);
macro_CPPMLToSimple_alreadySimple(int);
macro_CPPMLToSimple_alreadySimple(short);
macro_CPPMLToSimple_alreadySimple(char);
macro_CPPMLToSimple_alreadySimple(unsigned long);
macro_CPPMLToSimple_alreadySimple(unsigned int);
macro_CPPMLToSimple_alreadySimple(unsigned short);
macro_CPPMLToSimple_alreadySimple(unsigned char);
macro_CPPMLToSimple_alreadySimple(bool);


template<>
class CPPMLToSimple<Hash> {
public:
	static boost::python::object toSimple(const Hash& in)
		{
		return boost::python::object(hashToString(in));
		}

	static void fromSimple(Hash& out, boost::python::object in)
		{
		out = stringToHash(boost::python::extract<std::string>(in)());
		}
};


template<class T>
class CPPMLToSimpleGivenDirective<T, CPPMLDirectiveIsCppmlType<T> > {
public:
	typedef typename T::kind kind;
	typedef typename T::metadata metadata;

	static boost::python::object toSimple(const T& in)
		{
		return toSimple(in, kind());
		}

	static boost::python::object toSimple(const T& in, const ::CPPML::Kinds::tuple& kindSelector)
		{
		boost::python::object io = boost::python::tuple();

		CPPMLToSimpleGivenCppmlMetadata<T, kind, metadata>::toSimple(io, in);

		return io;
		}

	static boost::python::object toSimple(const T& in, const ::CPPML::Kinds::alternative& kindSelector)
		{
		boost::python::object io = boost::python::dict();

		CPPMLToSimpleGivenCppmlMetadata<T, kind, metadata>::toSimple(io, in);

		return io;
		}

	static void fromSimple(T& out, boost::python::object in)
		{
		CPPMLToSimpleGivenCppmlMetadata<T, kind, metadata>::fromSimple(out, in);
		}
};

/******************** tuples ****************************/

template<class T, class A1, class A2>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, ::CPPML::Chain<A1, A2> > {
public:
	//recursive forms
	static void toSimple(boost::python::object& io, const T& in)
		{
		CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, A1>::toSimple(io, in);
		CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, A2>::toSimple(io, in);
		}

	static void fromSimple(T& out, boost::python::object in)
		{
		CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, A1>::fromSimple(out, in);
		CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, A2>::fromSimple(out, in);
		}

};

template<class T>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, ::CPPML::Null> {
public:

	static void toSimple(boost::python::object& io, const T& in)
		{
		}
	static void fromSimple(T& out, boost::python::object in)
		{
		}
};

template<class T, class member_type_in, class accessor_in, const int32_t ix>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::tuple, 
							::CPPML::TupleMember<T, member_type_in, accessor_in, ix> > {
public:
	static void toSimple(boost::python::object& io, const T& in)
		{
		io = io + boost::python::make_tuple(
			cppmlToSimplePythonRepresentation(
				accessor_in::get(in)
				)
			);
		}
	static void fromSimple(T& out, boost::python::object in)
		{
		cppmlFromSimplePythonRepresentation(accessor_in::get(out), in[ix]);
		}
};


/******************************** alternatives *************************/

template<class T, class A1, class A2>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, ::CPPML::Chain<A1, A2> > {
public:
	//entrypoint forms
	static void fromSimple(T& out, const boost::python::object& in)
		{
		std::string tag = boost::python::extract<std::string>(in[0]);
		boost::python::object body = in[1];

		fromSimple(out, tag, body);
		}

	static boost::python::object toSimple(const T& in)
		{
		boost::python::object tr = boost::python::dict();

		lassert(toSimple(tr, in));

		return tr;
		}
	//recursive forms
	static bool toSimple(boost::python::object& out, const T& in)
		{
		if (CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, A1>::toSimple(out, in))
			return true;

		if (CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, A2>::toSimple(out, in))
			return true;

		return false;
		}

	static bool fromSimple(T& out, std::string tag, const boost::python::object& body)
		{
		if (CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, A1>::fromSimple(out, tag, body))
			return true;
		
		if (CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, A2>::fromSimple(out, tag, body))
			return true;

		return false;
		}
};


template<class T>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, ::CPPML::Null> {
public:
	static bool toSimple(boost::python::object& out, const T& in)
		{
		return false;
		}
	static bool fromSimple(T& out, std::string tag, const boost::python::object& body)
		{
		return false;
		}
};

template<class T, class member_type_in, class accessor_in>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, 
					::CPPML::Alternative<T, member_type_in, accessor_in> > {
public:

	static bool toSimple(boost::python::object& out, const T& in)
		{
		if (accessor_in::is(in))
			{
			out = boost::python::make_tuple(
				in.tagName(),
				cppmlToSimplePythonRepresentation(accessor_in::get(in))
				);

			return true;
			}

		return false;
		}
	static bool fromSimple(T& out, std::string tag, const boost::python::object& body)
		{
		if (accessor_in::name() == tag)
			{
			member_type_in m;
			cppmlFromSimplePythonRepresentation(m, body);

			out = T(m);

			return true;
			}

		return false;
		}
};


template<class T, class member_type_in, class accessor_in, const int32_t ix>
class CPPMLToSimpleGivenCppmlMetadata<T, ::CPPML::Kinds::alternative, 
				::CPPML::AlternativeCommonMember<T, member_type_in, accessor_in, ix> > {
public:
	static bool toSimple(boost::python::object& out, const T& in)
		{
		lassert(false);
		}
	static bool fromSimple(T& out, std::string tag, const boost::python::object& body)
		{
		lassert(false);
		}
};




