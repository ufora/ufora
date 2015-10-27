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
#include "VariableAllocator.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"

class VariableAllocatorWrapper :
		public native::module::Exporter<VariableAllocatorWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "FORA";
			}

		template<class T>
		static std::string	scopedPrettyPrinter(const T& in)
			{
			ScopedPyThreads threads;
			return prettyPrintString(in);
			}
		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			
			boost::python::class_<VariableAllocator, 
					boost::shared_ptr<VariableAllocator> >("VariableAllocator");
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<VariableAllocatorWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			VariableAllocatorWrapper>::registerWrapper();




