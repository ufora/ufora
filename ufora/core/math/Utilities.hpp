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
#ifndef base_math_Utilities_HPP_
#define base_math_Utilities_HPP_

#include <complex> 

namespace Ufora {
namespace math {

template<class scalar_type>
inline scalar_type	norm2(scalar_type inC)
	{
	return inC * inC;
	}
template<class scalar_type>
inline scalar_type	norm2(std::complex<scalar_type> inC)
	{
	return inC.real() * inC.real() + inC.imag() * inC.imag();
	}

template<class scalar_type>
inline scalar_type	sqrt2(void)
	{
	return 1.4142135623730951;
	}
	
	
template<class scalar_type>
inline scalar_type pi(void)
	{
	return 3.1415926535897931;
	}

template<class scalar_type>
inline scalar_type sqrt2pi(void)
	{
	return 2.5066282746310002;
	}


template<class T>
class VarianceFunction {
public:
		typedef T	result_type;
		
		T	operator()(T in) const
			{
			return in * in;
			}
};

template<class T>
class VarianceFunction<std::complex<T> > {
public:	
		typedef T	result_type;
		
		T	operator()(std::complex<T> in) const
			{
			return norm2(in);
			}
};

}
}

#endif

