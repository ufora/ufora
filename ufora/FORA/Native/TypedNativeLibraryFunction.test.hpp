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

#include "../../core/math/Hash.hpp"

namespace {

template<class R, class ... Args>
class TestCaseCall;

template<class R, class A1>
class TestCaseCall<R, A1> {
public:
	static R call(A1 a)
		{
		R tr((hash_type((int)a) + hash_type(11))[0]);

		return tr;
		}
};

template<class R, class A1, typename ... Args>
class TestCaseCall<R, A1, Args... > {
public:
	static R call(A1 a, Args ... args)
		{
		return R((hash_type((int)a) + hash_type((int)TestCaseCall<R, Args ...>::call(args ...)))[0]);
		}
};

}
