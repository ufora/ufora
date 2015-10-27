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

#ifdef TARGET_CUDA
#define NO_LASSERT 1
#endif

#ifndef NO_LASSERT

#include <boost/shared_ptr.hpp>
#include <sstream>
#include <iostream>
#include <stdexcept>
#include "debug/StackTrace.hpp"

#ifdef _WIN32

#define __PRETTY_FUNCTION__ "__PRETTY_FUNCTION__ not defined for WIN32"
#include <assert.h>
#define lassert(cond) assert(cond)
#define lassert_dump(cond, exp) { if (!(cond)) { std::cout << "failed " << #cond << "\n" << exp << "\n"; assert(false); throw; } }


#ifndef NO_STRONG_ASSERT
#define NO_STRONG_ASSERT 0
#endif

#ifndef NO_WEAK_ASSERT
#define NO_WEAK_ASSERT 0
#endif

#define strong_assert(cond)										\
if (!NO_STRONG_ASSERT) lassert(cond)							\

#define strong_assert_dump(cond, expr)							\
if (!NO_STRONG_ASSERT) lassert_dump(cond, expr)					\

#define weak_assert(cond)										\
if (!NO_WEAK_ASSERT) { lassert(cond); }							\

#define weak_assert_dump(cond, expr)							\
if (!NO_WEAK_ASSERT) { lassert_dump(cond, expr); }				\

#else

void lassert_check_interrupt(const std::string& inException);

#define lassert(cond)											\
																\
{																\
if (!(cond))													\
	{															\
	boost::shared_ptr<std::ostringstream>						\
		str__________(new std::ostringstream());				\
	*str__________ << "failed condition (" << #cond << ") on line "	\
		<< __LINE__ << ", in file " << __FILE__ << "\n"			\
		;														\
	*str__________ << "\n\n" << Ufora::debug::StackTrace::getStringTrace();	\
	lassert_check_interrupt(str__________->str());				\
	throw std::logic_error(str__________->str());				\
	}															\
}																\


#define lassert_dump(cond, expression)							\
																\
{																\
if (!(cond))													\
	{															\
	boost::shared_ptr<std::ostringstream>						\
		str__________(new std::ostringstream());				\
	*str__________ << "failed condition (" << #cond << ") on line "	\
		<< __LINE__ << ", in file " << __FILE__ << "\n";		\
	*str__________ << "\n\n" << expression << "\n";				\
	*str__________ << "\n\n" << Ufora::debug::StackTrace::getStringTrace();	\
	lassert_check_interrupt(str__________->str());				\
	throw std::logic_error(str__________->str());				\
	}															\
}																\


#define weak_assert(cond)										\
if (!NO_WEAK_ASSERT) { lassert(cond) }							\

#define weak_assert_dump(cond, expr)							\
if (!NO_WEAK_ASSERT) lassert_dump(cond, expr)					\

#define strong_assert(cond)										\
if (!NO_STRONG_ASSERT) lassert(cond)							\

#define strong_assert_dump(cond, expr)							\
if (!NO_STRONG_ASSERT) lassert_dump(cond, expr)					\

#ifndef NO_STRONG_ASSERT
#define NO_STRONG_ASSERT 0
#endif

#ifndef NO_WEAK_ASSERT
#define NO_WEAK_ASSERT 0
#endif

#define weak_assert_valid_index(container, index)				\
weak_assert(index >= 0 && index < container.size());			\

#endif

#else

#define lassert(cond)
#define lassert_dump(cond, dump)

#define strong_assert(cond)
#define strong_assert_dump(cond, dump)

#define weak_assert(cond)
#define weak_assert_dump(cond, dump)

#define weak_assert_valid_index(contianer, index)

#endif

