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
#include "RateLimitedChannelGroup.hpp"

#include <boost/python.hpp>
#include <boost/random.hpp>

#include "../native/Registrar.hpp"
#include "../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"

class RateLimitedStringChannelGroupWrapper :
		public native::module::Exporter<RateLimitedStringChannelGroupWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "StringChannel";
			}

		static boost::python::object createRateLimitedStringChannelGroup(
						PolymorphicSharedPtr<CallbackScheduler> scheduler,
						double throughput
						)
			{
			return boost::python::object(
				PolymorphicSharedPtr<RateLimitedChannelGroup<std::string, std::string> >(
					new RateLimitedChannelGroup<std::string, std::string>(
						scheduler,
						boost::function1<double, std::string>([](std::string s) { return (double)s.size(); }),
						boost::function1<double, std::string>([](std::string s) { return (double)s.size(); }),
						throughput
						)
					)
				);
			}
				
		void exportPythonWrapper()
			{
			using namespace boost::python;
				
			typedef RateLimitedChannelGroup<std::string, std::string> group_type;

			typedef typename group_type::pointer_type ptr_type;

			class_<ptr_type>("RateLimitedStringChannelGroup", no_init)
				.macro_psp_py_def("wrap", group_type::wrap)
				;

			def("createRateLimitedStringChannelGroup", createRateLimitedStringChannelGroup);
			}
};


//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<RateLimitedStringChannelGroupWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			RateLimitedStringChannelGroupWrapper>::registerWrapper();


