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
#define BOOST_TEST_DYN_LINK
#define BOOST_TEST_ALTERNATIVE_INIT_API
#include <boost/test/unit_test.hpp>

#include "../native/module.hpp"
#include <vector>
#include <string>

#include <stdint.h>
#include <boost/python.hpp>
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/python/ScopedPyThreads.hpp"


namespace {

bool init_unit_test()
	{
	return true;
	}
	

int test(void)
	{
	char substr[3];
	substr[0] = 0;
	
	char* toss[2] = { substr, 0 };
	
	return ::boost::unit_test::unit_test_main( &init_unit_test, 1, toss);
	}
int testWithArgs(boost::python::object args)
	{
	std::vector<std::string> strings;
	std::vector<char*> charptrs;
	char data[1];
	data[0] = 0;
	
	charptrs.push_back(data);
	
	long len = boost::python::extract<int>( args.attr("__len__")());
	
	for (long k = 0; k < len;k++)
		{
		strings.push_back(boost::python::extract<std::string>(args[k]));
		strings.back().c_str();
		charptrs.push_back(&strings.back()[0]);
		}
	
	//make sure there's a null terminator
	charptrs.push_back(0);
	
	return ::boost::unit_test::unit_test_main( &init_unit_test, charptrs.size()-1, &charptrs[0]);
	}

#ifdef COVERAGE_BUILD
extern "C" void __gcov_flush();
#endif

void gcov_flush()
	{
#ifdef COVERAGE_BUILD
	__gcov_flush();
#endif
	}

}

class UnitTestMainlineWrapper :
	public native::module::Exporter<UnitTestMainlineWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "Tests";
		}

	static void forceStackdump()
		{
		fflush(stdout);
		fflush(stderr);
		((char*)0)[0] = 0;
		}

	void exportPythonWrapper()
		{
		boost::python::def("forceStackdump", forceStackdump);
		boost::python::def("test", test);
		boost::python::def("test", testWithArgs);
		boost::python::def("gcov_flush", gcov_flush);
        }
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<UnitTestMainlineWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<UnitTestMainlineWrapper>::registerWrapper();

