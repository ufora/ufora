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
#include <stdint.h>
#include <vector>
#include <string>
#include "../../native/Registrar.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../Runtime.hppml"
#include "TypedCfgStats.hppml"
#include <boost/python.hpp>

class TypedCfgStatsWrapper :
		public native::module::Exporter<TypedCfgStatsWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<TypedCfgStats> >("TypedCfgStats", no_init)
                .def("resolveAxiomDirectly", 
                        macro_polymorphicSharedPtrFuncFromMemberFunc(TypedCfgStats::resolveAxiomDirectly)
                    )
                ;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<TypedCfgStatsWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			TypedCfgStatsWrapper>::registerWrapper();

