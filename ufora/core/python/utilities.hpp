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
#include "../lassert.hpp"
#include "../containers/ImmutableTreeVector.hppml"
#include "../containers/ImmutableTreeMap.hppml"
#include "../numpy/TypedNumpyWrapper.hpp"
#include "../math/Nullable.hpp"
#include "../Logging.hpp"
#include "../PolymorphicSharedPtr.hpp"
#include <vector>


namespace Ufora {
namespace python {

//take a pair of C++ iterators and append their elements onto the end of a new python
//list. The objects must be convertable to python objects.
template<class iterator_type>
boost::python::object iteratorPairToList(iterator_type begin, iterator_type end)
	{
	boost::python::list l;
	while (begin != end)
		{
		l.append(*begin);
		begin++;
		}

	return l;
	}

//take a pair of C++ iterators and append their elements onto the end of a new python
//list, applying inAdapter to each element. The result of the inAdapter call
// must be convertable to a python object.
template<class iterator_type, class adapter_type>
boost::python::object iteratorPairToList(iterator_type begin, iterator_type end, const adapter_type& inAdapter)
	{
	boost::python::list l;
	while (begin != end)
		{
		l.append(inAdapter(*begin));
		begin++;
		}

	return l;
	}

//take a C++ class that exposes begin/end pairs and pack it into a new python list.
template<class T>
boost::python::object containerWithBeginEndToList(const T& in)
	{
	return iteratorPairToList(in.begin(), in.end());
	}

//take a C++ class that exposes begin/end pairs and pack it into a new python list.
//applies 'inAdapter' to every element
template<class T, class adapter_type>
boost::python::object containerWithBeginEndToList(const T& in, const adapter_type& inAdapter)
	{
	return iteratorPairToList(in.begin(), in.end(), inAdapter);
	}

template<class T>
class	Converter {
public:
		static boost::python::object	toPython(const T& in)
			{
			return boost::python::object(in);
			}
		static void toCPP(boost::python::object o, T& outT)
			{
			lassert(boost::python::extract<T>(o).check());
			outT = boost::python::extract<T>(o);
			}
		static void toCPPAsInit(boost::python::object o, T& outT)
			{
			lassert(boost::python::extract<T>(o).check());
			new (&outT) T(boost::python::extract<T>(o));
			}
};

template<class T>
void	toCPP(boost::python::object o, T& outT)
	{
	try {
		Converter<T>::toCPP(o, outT);
		}
	catch(...)
		{
		LOG_WARN << "RANDOM TOCPP... " << Ufora::debug::StackTrace::demangle(typeid(T).name()) << "\n";
		}
	}
template<class T>
void	toCPPAsInit(boost::python::object o, T& outT)
	{
	try {
		Converter<T>::toCPPAsInit(o, outT);
		}
	catch(...)
		{
		LOG_WARN << "RANDOM TOCPP INIT " << Ufora::debug::StackTrace::demangle(typeid(T).name()) << "...\n";
		}
	}
template<class T>
boost::python::object	toPython(const T& inT)
	{
	try {
		return Converter<T>::toPython(inT);
		}
	catch(...)
		{
		LOG_WARN << "RANDOM...\n";
		return boost::python::object("FAILED");
		}
	}

template<class T>
std::tuple<T> toTuple(boost::python::tuple pyTuple)
	{
	lassert(boost::python::len(pyTuple) == 1);
	boost::python::extract<T> extractor(pyTuple[0]);
	lassert(extractor.check());
	
	return std::make_tuple(extractor());
	}

template<class T1, class T2>
std::tuple<T1, T2> toTuple(boost::python::tuple pyTuple)
	{
	lassert(boost::python::len(pyTuple) == 2);
	boost::python::extract<T1> extractor1(pyTuple[0]);
	lassert(extractor1.check());
	boost::python::extract<T2> extractor2(pyTuple[1]);
	lassert(extractor2.check());
	
	return std::make_tuple(extractor1(), extractor2());
	}

template<class T1, class T2, class T3>
std::tuple<T1, T2, T3> toTuple(boost::python::tuple pyTuple)
	{
	lassert(boost::python::len(pyTuple) == 3);
	boost::python::extract<T1> extractor1(pyTuple[0]);
	lassert(extractor1.check());
	boost::python::extract<T2> extractor2(pyTuple[1]);
	lassert(extractor2.check());
	boost::python::extract<T3> extractor3(pyTuple[2]);
	lassert(extractor3.check());
	
	return std::make_tuple(extractor1(), extractor2(), extractor3());
	}

template<class T1, class T2, class T3, class T4>
std::tuple<T1, T2, T3, T4> toTuple(boost::python::tuple pyTuple)
	{
	lassert(boost::python::len(pyTuple) == 4);
	boost::python::extract<T1> extractor1(pyTuple[0]);
	lassert(extractor1.check());
	boost::python::extract<T2> extractor2(pyTuple[1]);
	lassert(extractor2.check());
	boost::python::extract<T3> extractor3(pyTuple[2]);
	lassert(extractor3.check());
	boost::python::extract<T4> extractor4(pyTuple[3]);
	lassert(extractor4.check());
	
	return std::make_tuple(extractor1(), extractor2(), extractor3(), extractor4());
	}

template<>
class Converter<vector<double> > {
public:
		typedef double	T;

		static void	toCPPAsInit(boost::python::object o, vector<T>& outT)
			{
			new (&outT) vector<T>();
			toCPP(o, outT);
			}
		static void	toCPP(boost::python::object o, vector<T>& outT)
			{
			outT.resize(0);

			try {
				::Ufora::numpy::TypedNumpyWrapper<double, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			try {
				Ufora::numpy::TypedNumpyWrapper<float, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			//generic iterator...
			boost::python::object it = o.attr("__iter__")();

			try {
				while(1)
					{
					outT.resize(outT.size() + 1);
					Converter<T>::toCPP(it.attr("next")(), outT.back());
					}
				}
			catch(...)
				{
				outT.resize(outT.size()-1);
				PyErr_Clear();
				}
			}

		static boost::python::object	toPython(const vector<T>& inT)
			{
			boost::python::object numpy = boost::python::import("numpy");

			boost::python::object o = numpy.attr("zeros")(inT.size()).attr("astype")("double");
			::Ufora::numpy::TypedNumpyWrapper<T, 1> wrap(o);

			for (int32_t k = 0; k < inT.size();k++)
				o[k] = inT[k];

			return o;
			}
};

template<>
class Converter<vector<std::complex<double> > > {
public:
		typedef std::complex<double>	T;

		static void	toCPPAsInit(boost::python::object o, vector<T>& outT)
			{
			new (&outT) vector<T>();
			toCPP(o, outT);
			}
		static void	toCPP(boost::python::object o, vector<T>& outT)
			{
			outT.resize(0);

			try {
				Ufora::numpy::TypedNumpyWrapper<std::complex<double>, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			try {
				Ufora::numpy::TypedNumpyWrapper<std::complex<float>, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			//generic iterator...
			boost::python::object it = o.attr("__iter__")();

			try {
				while(1)
					{
					outT.resize(outT.size() + 1);
					Converter<T>::toCPP(it.attr("next")(), outT.back());
					}
				}
			catch(...)
				{
				outT.resize(outT.size()-1);
				PyErr_Clear();
				}
			}

		static boost::python::object	toPython(const vector<T>& inT)
			{
			boost::python::object numpy = boost::python::import("numpy");

			boost::python::object o = numpy.attr("zeros")(inT.size()).attr("astype")("complex");
			Ufora::numpy::TypedNumpyWrapper<T, 1> wrap(o);

			for (int32_t k = 0; k < inT.size();k++)
				o[k] = inT[k];

			return o;
			}
};

template<>
class Converter<vector<float> > {
public:
		typedef float	T;

		static void	toCPPAsInit(boost::python::object o, vector<T>& outT)
			{
			new (&outT) vector<T>();
			toCPP(o, outT);
			}
		static void	toCPP(boost::python::object o, vector<T>& outT)
			{
			outT.resize(0);

			try {
				Ufora::numpy::TypedNumpyWrapper<float, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			try {
				Ufora::numpy::TypedNumpyWrapper<double, 1> wrap(o);
				outT.resize(wrap.size());
				for (int32_t k = 0; k < outT.size(); k++)
					outT[k] = wrap[k];
				return;
				}
			catch(...)
				{
				}

			//generic iterator...
			boost::python::object it = o.attr("__iter__")();

			try {
				while(1)
					{
					outT.resize(outT.size() + 1);
					Converter<T>::toCPP(it.attr("next")(), outT.back());
					}
				}
			catch(...)
				{
				outT.resize(outT.size()-1);
				PyErr_Clear();
				}
			}

		static boost::python::object	toPython(const vector<T>& inT)
			{
			boost::python::object numpy = boost::python::import("numpy");

			boost::python::object o = numpy.attr("zeros")(inT.size()).attr("astype")("float");
			Ufora::numpy::TypedNumpyWrapper<T, 1> wrap(o);

			for (int32_t k = 0; k < inT.size();k++)
				o[k] = inT[k];

			return o;
			}
};

template<class T>
class Converter<vector<T> > {
public:
		static void	toCPP(boost::python::object o, vector<T>& outT)
			{
			outT.clear();

			boost::python::object it = o.attr("__iter__")();

			try {
				while(1)
					{
					char dat[sizeof(T)];
					Converter<T>::toCPPAsInit(it.attr("next")(), ((T*)dat)[0]);
					outT.push_back(((T*)dat)[0]);
					((T*)dat)->~T();
					}
				}
			catch(...)
				{
				PyErr_Clear();
				}
			}

		static boost::python::object	toPython(const vector<T>& inT)
			{
			boost::python::list o = boost::python::list();

			for (int32_t k = 0; k < inT.size();k++)
				o.append(Converter<T>::toPython(inT[k]));
			return o;
			}
};

template<class T>
class Converter<ImmutableTreeVector<T> > {
public:
		static void	toCPP(boost::python::object o, ImmutableTreeVector<T>& outT)
			{
			outT = ImmutableTreeVector<T>();

			boost::python::object it = o.attr("__iter__")();

			while(1)
				{
				T t;

				boost::python::object o;
				try {
					o = it.attr("next")();
					}
				catch(...)
					{
					PyErr_Clear();
					return;
					}

				Converter<T>::toCPP(o, t);
				outT = outT + t;
				}
			}

		static boost::python::object	toPython(const ImmutableTreeVector<T>& inT)
			{
			boost::python::list o = boost::python::list();

			for (int32_t k = 0; k < inT.size();k++)
				o.append(Converter<T>::toPython(inT[k]));

			return o;
			}
};

template<class T1, class T2>
class Converter<ImmutableTreeMap<T1, T2> > {
public:
		static void	toCPP(boost::python::object o, ImmutableTreeMap<T1, T2>& outT)
			{
			outT = ImmutableTreeMap<T1, T2>();

			boost::python::object it = o.attr("__iter__")();

			while(1)
				{
				T1 t1;
				T2 t2;
				
				boost::python::object key;
				try {
					key = it.attr("next")();
					}
				catch(...)
					{
					PyErr_Clear();
					return;
					}

				Converter<T1>::toCPP(key, t1);
				Converter<T2>::toCPP(o[key], t2);
				
				outT = outT + make_pair(t1, t2);
				}
			}

		static boost::python::object	toPython(const ImmutableTreeMap<T1, T2>& inT)
			{
			boost::python::dict o = boost::python::dict();

			for (int32_t k = 0; k < inT.size();k++)
				o[Converter<T1>::toPython(inT.pairAtPosition(k).first)]
				 					= Converter<T2>::toPython(inT.pairAtPosition(k).second);

			return o;
			}
};

template<class T1, class T2>
class Converter<pair<T1, T2> > {
public:
		static void	toCPPAsInit(boost::python::object o, pair<T1, T2>& outT)
			{
			new (&outT) pair<T1, T2>();
			toCPP(o, outT);
			}
		boost::python::object	toPython(const pair<T1, T2>& inT)
			{
			return boost::python::make_tuple(Converter<T1>::toPython(inT.first), Converter<T2>::toPython(inT.second));
			}

		static void toCPP(boost::python::object o, pair<T1, T2>& outT)
			{
			try {
				Converter<T1>::toCPP(o[0], outT.first);
				Converter<T2>::toCPP(o[1], outT.second);
				}
			catch(...)
				{
				PyErr_Clear();
				}
			}
};

template<class T1>
class Converter<Nullable<T1> > {
public:
		boost::python::object	toPython(const Nullable<T1>& inT)
			{
			if (!inT)
				return boost::python::object();
			return boost::python::object(Converter<T1>::toPython(*inT));
			}

		static void toCPP(boost::python::object o, Nullable<T1>& outT)
			{
			if (!o.ptr())
				{
				outT = null();
				return;
				}

			try {
				T1 final;

				Converter<T1>::toCPP(o, final);

				outT = final;
				}
			catch(...)
				{
				PyErr_Clear();
				}
			}
};
class Holder {
public:
		Holder(const string& inEval, const string& inSpace)
			{
			mEval = inEval;
			mSpace = inSpace;
			mInitialized = false;
			}
		boost::python::object get(void)
			{
			if (!mInitialized)
				{
				boost::python::object ns = boost::python::import(mSpace.c_str()).attr("__dict__");
				o = boost::python::eval(mEval.c_str(), ns, ns);
				mInitialized = true;
				}
			return o;
			}
private:
		bool mInitialized;
		boost::python::object o;
		string mEval, mSpace;
};

inline boost::python::object evalInModule(const char *inObjectName, const char *inNamespace)
	{
	boost::python::object ns = boost::python::import(inNamespace).attr("__dict__");
	return boost::python::eval(inObjectName, ns, ns);
	}

inline boost::python::object isInstance(boost::python::object inO1, boost::python::object inO2)
	{
	static boost::python::object _isInstance;
	if (_isInstance == boost::python::object())
		_isInstance = evalInModule("__builtin__.isinstance", "site");

	return _isInstance(inO1, inO2);
	}

inline string pyToString(boost::python::object o)
	{
	lassert(boost::python::extract<string>(boost::python::str(o)).check());
	return boost::python::extract<string>(boost::python::str(o));
	}

inline unsigned long id(const boost::python::object& inO)
	{
	return (unsigned long)inO.ptr();
	}

};
};



