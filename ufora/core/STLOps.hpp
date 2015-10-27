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
#ifndef STLOps_hpp_
#define STLOps_hpp_

#include <vector>
#include <set>
#include <map>

template<class T>
inline std::vector<T> operator+(const std::vector<T>& l, const std::vector<T>& r)
	{
	std::vector<T> v0 = l;
	v0.insert(v0.end(), r.begin(), r.end());
	return v0;
	}
template<class T>
inline std::vector<T>& operator+=(std::vector<T>& l, const std::vector<T>& r)
	{
	l.insert(l.end(), r.begin(), r.end());
	return l;
	}
template<class T>
inline std::vector<T> operator+(const std::vector<T>& l, const T& r)
	{
	std::vector<T> v0 = l;
	v0.push_back(r);
	return v0;
	}
template<class T>
inline std::vector<T>& operator+=(std::vector<T>& l, const T& r)
	{
	l.push_back(r);
	return l;
	}
template<class T>
inline std::vector<T> operator+(const T& l, const std::vector<T>& r)
	{
	std::vector<T> v0;
	v0.push_back(l);
	v0.insert(v0.end(), r.begin(), r.end());
	return v0;
	}

template <class T>
bool operator == (const T& lhs,const std::set<T>& rhs)
	{
	return rhs.find(lhs) != rhs.end();
	}
template <class T>
bool operator != (const T& lhs,const std::set<T>& rhs)
	{
	return rhs.find(lhs) == rhs.end();
	}
template <class T>
std::set<T>& operator -= (std::set<T>& lhs, const T& rhs)
	{
	lhs.erase(rhs);
	return lhs;
	}
template <class T>
std::set<T>& operator += (std::set<T>& lhs, const T& rhs)
	{
	lhs.insert(rhs);
	return lhs;
	}
template <class T, class T2>
std::set<T>& operator += (std::set<T>& lhs, const std::set<T2>& rhs)
	{
	for (typename std::set<T2>::const_iterator it = rhs.begin(); it  != rhs.end(); ++it)
		lhs.insert(*it);
	return lhs;
	}
template <class T, class T2>
std::set<T>& operator += (std::set<T>& lhs, const std::vector<T2>& rhs)
	{
	for (typename std::vector<T2>::const_iterator it = rhs.begin(); it  != rhs.end(); ++it)
		lhs.insert(*it);
	return lhs;
	}
template <class T, class T2>
std::set<T>& operator -= (std::set<T>& lhs, const std::set<T2>& rhs)
	{
	for (typename std::set<T2>::const_iterator it = rhs.begin(); it  != rhs.end(); ++it)
		lhs.erase(*it);
	return lhs;
	}
template <class T, class T2>
std::set<T>& operator -= (std::set<T>& lhs, const std::vector<T2>& rhs)
	{
	for (typename std::vector<T2>::const_iterator it = rhs.begin(); it  != rhs.end(); ++it)
		lhs.erase(*it);
	return lhs;
	}
template <class T, class T2>
bool operator == (const T& lhs,const std::map<T, T2>& rhs)
	{
	return rhs.find(lhs) != rhs.end();
	}
template <class T, class T2>
bool operator != (const T& lhs,const std::map<T, T2>& rhs)
	{
	return rhs.find(lhs) == rhs.end();
	}


template<class T>
T pop(std::set<T>& io)
	{
	T tr = *io.begin();
	io.erase(tr);
	return tr;
	}

#endif

