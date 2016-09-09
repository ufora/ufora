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
#ifndef TypedNumpyWrapper_H_
#define TypedNumpyWrapper_H_

#include "NumpyArrays.hpp"
#include <stdint.h>
#include <boost/python.hpp>
#include <boost/python/raw_function.hpp>
#include <iostream>
#include <complex>
#include <vector>
#include <string>
#include <sstream>
#include "../python/ScopedPyThreads.hpp"

using namespace std;

namespace Ufora {

namespace numpy {

template<class T>
class TypeToNumpyNumber;

template<int32_t val>
class NumpyNumberToType;

#define local_numppy_hpp_typemapper(nsym, locsym)										\
template<> class TypeToNumpyNumber<locsym > { public: const static int32_t result = nsym; };	\
template<> class NumpyNumberToType<nsym> { public: typedef locsym result; };			\


#define local_numppy_hpp_stringmapper(nsym, locsym)										\
{if (numpyID == nsym)																	\
	return std::string(#locsym);}														\


inline string numpyNumberToTypename(int32_t numpyID)
	{
	local_numppy_hpp_stringmapper(NPY_BYTE, npy_int8);
	local_numppy_hpp_stringmapper(NPY_FLOAT, npy_float);
	local_numppy_hpp_stringmapper(NPY_DOUBLE, npy_double);
	local_numppy_hpp_stringmapper(NPY_LONGDOUBLE, npy_longdouble);
	local_numppy_hpp_stringmapper(NPY_CFLOAT, std::complex<npy_float>);
	local_numppy_hpp_stringmapper(NPY_CDOUBLE, std::complex<npy_double>);
	local_numppy_hpp_stringmapper(NPY_CLONGDOUBLE, std::complex<npy_longdouble>);
	local_numppy_hpp_stringmapper(NPY_INT, npy_int);
	local_numppy_hpp_stringmapper(NPY_LONG, npy_long);
	local_numppy_hpp_stringmapper(NPY_LONGLONG, npy_longlong);

	return "<bad ID!>";
	}



local_numppy_hpp_typemapper(NPY_BYTE, npy_int8);
local_numppy_hpp_typemapper(NPY_FLOAT, npy_float);
local_numppy_hpp_typemapper(NPY_DOUBLE, npy_double);
local_numppy_hpp_typemapper(NPY_CFLOAT, std::complex<npy_float>);
local_numppy_hpp_typemapper(NPY_CDOUBLE, std::complex<npy_double>);
local_numppy_hpp_typemapper(NPY_INT, npy_int);
local_numppy_hpp_typemapper(NPY_LONG, npy_long);
local_numppy_hpp_typemapper(NPY_LONGLONG, npy_longlong);

// in Visual Studio int32_t double and double are the same type so if you try to specialize the template on both it says there
// are conflicting specializations for the same types and gives errors
#if defined(__APPLE__) || defined(__linux__)
    local_numppy_hpp_typemapper(NPY_CLONGDOUBLE, std::complex<npy_longdouble>);
    local_numppy_hpp_typemapper(NPY_LONGDOUBLE, npy_longdouble);
#endif





template<class T, int32_t dim>
class TypedNumpyWrapper {
public:
		typedef	T	elt_type;

		TypedNumpyWrapper(boost::python::object inPyArray)
			{
			if (((PyArrayObject*)inPyArray.ptr())->nd != dim)
				throw std::logic_error("wrong number of dimensions in TypedNumpyWrapper assignment");
			if (((PyArrayObject*)inPyArray.ptr())->descr->type_num != TypeToNumpyNumber<T>::result)
				throw std::logic_error(
					"wrong type. expected "
					+ std::string(typeid(T).name())
					+ " but got "
					+ numpyNumberToTypename(((PyArrayObject*)inPyArray.ptr())->descr->type_num));

			mPyArray = inPyArray;
			mPtr = (PyArrayObject*)mPyArray.ptr();
			}
		TypedNumpyWrapper(const TypedNumpyWrapper& in)
			{
			mPyArray = in.mPyArray;
			mPtr = (PyArrayObject*)mPyArray.ptr();
			}

		uint32_t dimensions(void) const
			{
			return pyArrayPtr()->nd;
			}
		uint32_t size(int32_t inDim = 0) const
			{
			if (inDim < 0 || inDim >= pyArrayPtr()->nd)
				throw std::logic_error("bad dimension");

			return pyArrayPtr()->dimensions[inDim];
			}
		uint32_t stride(int32_t inDim = 0) const
			{
			if (inDim < 0 || inDim >= pyArrayPtr()->nd)
				throw std::logic_error("bad dimension");

			return pyArrayPtr()->strides[inDim];
			}

		T& operator[](int32_t inIx) const
			{
			throw std::logic_error("wrong # of dimensions");
			}
		T& operator()(int32_t inIx0, int32_t inIx1) const
			{
			if (dimensions() != 2.0)
				throw std::logic_error("wrong # of dimensions");

			if (inIx0 < 0 || inIx0 > size(0))
				throw std::logic_error("bad index 0");
			if (inIx1 < 0 || inIx1 > size(1))
				throw std::logic_error("bad index 1");
			return *(T*)(pyArrayPtr()->data + pyArrayPtr()->strides[0] * inIx0 + pyArrayPtr()->strides[1] * inIx1);
			}

private:
		PyArrayObject*	pyArrayPtr(void) const
			{
			return mPtr;
			}
		PyArrayObject*		  mPtr;
		boost::python::object mPyArray;
};

template<class T>
class TypedNumpyWrapper<T, 1> {
public:
		const static int32_t 	dim = 1;
		typedef	T			elt_type;

		TypedNumpyWrapper(boost::python::object inPyArray)
			{
            globals["numpy"] = boost::python::import("numpy");
			if (((PyArrayObject*)inPyArray.ptr())->nd != dim)
				throw std::logic_error("wrong number of dimensions in TypedNumpyWrapper assignment");
			if (((PyArrayObject*)inPyArray.ptr())->descr->type_num != TypeToNumpyNumber<T>::result)
				throw std::logic_error(
					"wrong type. expected "
					+ std::string(typeid(T).name())
					+ " but got "
					+ numpyNumberToTypename(((PyArrayObject*)inPyArray.ptr())->descr->type_num));

			mPyArray = inPyArray;

			mPtr = (PyArrayObject*)mPyArray.ptr();
			}
		TypedNumpyWrapper(const TypedNumpyWrapper& in)
			{
            globals["numpy"] = boost::python::import("numpy");
			mPyArray = in.mPyArray;
			mPtr = (PyArrayObject*)mPyArray.ptr();
			}

		TypedNumpyWrapper(PyArrayObject* in)
			{
			Py_XINCREF(in);	// increase ref count!!!
			mPtr = in;
			mPyArray = boost::python::object(boost::python::handle<>((PyObject*)in)); // for later python access
			}

		TypedNumpyWrapper(int32_t inSize)
            {
            globals["numpy"] = boost::python::import("numpy");
            ostringstream tr;
            tr << "numpy.zeros(" << inSize << ", " << "dtype=numpy.sctypeDict[" << TypeToNumpyNumber<T>::result << "])";
            mPyArray = boost::python::eval(boost::python::str(tr.str()), globals, globals);
			mPtr = (PyArrayObject*)mPyArray.ptr();
            }

        boost::python::object toPython(void)
            {
            return mPyArray;
            }

		void toVector(std::vector<T> &out) const
			{
			out.resize(size());

			for (int32_t k = 0; k < size(); k++)
				out[k] = (*this)[k];
			}
		std::vector<T> toVector(void) const
			{
			std::vector<T> tr;
			toVector(tr);
			return tr;
			}
		uint32_t dimensions(void) const
			{
			return pyArrayPtr()->nd;
			}
		uint32_t size(int32_t inDim = 0) const
			{
			if (inDim < 0 || inDim >= pyArrayPtr()->nd)
				throw std::logic_error("bad dimension");

			return pyArrayPtr()->dimensions[inDim];
			}
		uint32_t stride(int32_t inDim = 0) const
			{
			if (inDim < 0 || inDim >= pyArrayPtr()->nd)
				throw std::logic_error("bad dimension");

			return pyArrayPtr()->strides[inDim];
			}

		T& operator[](int32_t inIx) const
			{
			if (inIx < 0 || inIx >= size(0))
				throw std::logic_error("bad index");

			return *(T*)(pyArrayPtr()->data + pyArrayPtr()->strides[0] * inIx);
			}

		void resize(uint32_t inSize)
			{
            mPyArray = globals["numpy"].attr("resize")(mPyArray, inSize);
            mPtr = (PyArrayObject*)mPyArray.ptr();
			}



		template<class T2>
		vector<T2> toDoubles(void)
			{
			lassert(size() % 2 == 0);
			vector<T2> tr;
			for (int32_t i = 0; i < size() / 2; i++)
				tr.push_back(T2(operator[](i * 2), operator[](i * 2 + 1)));
			return tr;
			}
		template<class T2>
		vector<T2> toTriples(void)
			{
			lassert(size() % 3 == 0);
			vector<T2> tr;
			for (int32_t i = 0; i < size() / 3; i++)
				tr.push_back(T2(operator[](i * 3), operator[](i * 3 + 1), operator[](i * 3 + 2)));
			return tr;
			}
		template<class T2>
		vector<T2> toQuads(void)
			{
			lassert(size() % 4 == 0);
			vector<T2> tr;
			for (int32_t i = 0; i < size() / 4; i++)
				tr.push_back(T2(operator[](i * 4), operator[](i * 4 + 1), operator[](i * 4 + 2), operator[](i * 4 + 3)));
			return tr;
			}





private:
		boost::python::object 	mPyArray;
        boost::python::dict     globals;
		PyArrayObject* 			mPtr;

		PyArrayObject*	pyArrayPtr(void) const
			{
			return mPtr;
			}
};







class NumpyWrapper {
public:
		NumpyWrapper(boost::python::object o)
			{
			if (!PyArray_Check(o.ptr()))
				throw std::logic_error("not a python array");
			mPyArray = o;
			}
		NumpyWrapper(const NumpyWrapper& in)
			{
			mPyArray = in.mPyArray;
			}

		template<class T, int32_t dim>
		TypedNumpyWrapper<T, dim> cast(void)
			{
			return TypedNumpyWrapper<T, dim>(mPyArray);
			}

		uint32_t dimensions(void) const
			{
			return pyArrayPtr()->nd;
			}
		uint32_t size(int32_t inDim = 0) const
			{
			if (inDim < 0 || inDim >= pyArrayPtr()->nd)
				throw std::logic_error("bad dimension");

			return pyArrayPtr()->dimensions[inDim];
			}

#define local_numpy_hpp_apply(t)													\
					switch(pyArrayPtr()->nd)											\
						{															\
						case 0:	in(TypedNumpyWrapper<t, 0>(mPyArray)); break;	\
						case 1:	in(TypedNumpyWrapper<t, 1>(mPyArray)); break;	\
						case 2:	in(TypedNumpyWrapper<t, 2>(mPyArray)); break;	\
						case 3:	in(TypedNumpyWrapper<t, 3>(mPyArray)); break;	\
						case 4:	in(TypedNumpyWrapper<t, 4>(mPyArray)); break;	\
						default: throw std::logic_error("bad dimension");			\
						}

#define local_numppy_hpp_map(t1, t2) if (pyArrayPtr()->descr->type_num == t1) { local_numpy_hpp_apply(t2); return; }

		template<class func_type>
		void apply(const func_type& in) const
			{
			/*types for NUMPY are
                    NPY_BYTE, NPY_UBYTE,
                    NPY_SHORT, NPY_USHORT,
                    NPY_INT, NPY_UINT,
                    NPY_LONG, NPY_ULONG,
                    NPY_LONGLONG, NPY_ULONGLONG,
                    NPY_FLOAT, NPY_DOUBLE, NPY_LONGDOUBLE,
                    NPY_CFLOAT, NPY_CDOUBLE, NPY_CLONGDOUBLE, */

            local_numppy_hpp_map(NPY_BYTE, npy_int8);
            local_numppy_hpp_map(NPY_FLOAT, npy_float);
			local_numppy_hpp_map(NPY_DOUBLE, npy_double);
			local_numppy_hpp_map(NPY_LONGDOUBLE, npy_longdouble);
			local_numppy_hpp_map(NPY_CFLOAT, std::complex<npy_float>);
			local_numppy_hpp_map(NPY_CDOUBLE, std::complex<npy_double>);
			local_numppy_hpp_map(NPY_CLONGDOUBLE, std::complex<npy_longdouble>);
			local_numppy_hpp_map(NPY_INT, npy_int);
			local_numppy_hpp_map(NPY_LONG, npy_long);
			local_numppy_hpp_map(NPY_LONGLONG, npy_longlong);


			throw std::logic_error("unknown numpy type");
			}

private:
		PyArrayObject*	pyArrayPtr(void) const
			{
			return (PyArrayObject*)mPyArray.ptr();
			}
		boost::python::object mPyArray;
};

} // end numpy namespace

}

#endif

