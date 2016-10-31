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
#include "Platform.hpp"

#ifdef BSA_PLATFORM_WINDOWS
#define BOOST_TEST_DYN_LINK
#endif

#include <boost/test/unit_test.hpp>

#define BOOST_TEST_USE_CPPML_PRINTER( T )                               \
namespace boost { namespace test_tools {								\
template<>																\
struct print_log_value<T> {												\
	void operator()( std::ostream& os, T const& t )						\
		{																\
		os << prettyPrintString(t);										\
		}																\
};																		\
}}																		// End of macro.

