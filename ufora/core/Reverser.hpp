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

template<class T>
class Reverser {
public:
	Reverser(const T& in) : m(in)
		{
		}

	typename T::const_reverse_iterator begin() const
		{
		return m.rbegin();
		}

	typename T::const_reverse_iterator end() const
		{
		return m.rend();
		}

private:
	const T& m;
};

template<class T>
Reverser<T> reverse(const T& in)
	{
	return Reverser<T>(in);
	}

