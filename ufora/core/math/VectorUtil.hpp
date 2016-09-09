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
#ifndef base_VectorUtil_hpp_
#define base_VectorUtil_hpp_

#include <vector>

namespace FOO {
template<class T>
std::vector<T> operator+(const std::vector<T>& in, const std::vector<T>& inR)
	{
	std::vector<T> l(in);
	l.insert(l.end(), inR.begin(), inR.end());
	return l;
	}

template<class T>
std::vector<T> operator+(const std::vector<T>& in, const T& inR)
	{
	std::vector<T> l(in);
	l.insert(l.end(), inR);
	return l;
	}
template<class T>
std::vector<T> operator+(const T& inL, const std::vector<T>& in)
	{
	std::vector<T> l;

	l.push_back(inL);
	l.insert(in.begin(), in.end());

	return l;
	}
}


#endif

