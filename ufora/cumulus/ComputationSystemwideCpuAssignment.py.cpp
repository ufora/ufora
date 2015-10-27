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
#include "ComputationSystemwideCpuAssignment.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../FORA/python/FORAPythonUtil.hppml"
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"

using namespace Cumulus;

class ComputationSystemwideCpuAssignmentWrapper :
		public native::module::Exporter<ComputationSystemwideCpuAssignmentWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "Cumulus";
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			boost::python::object cls = 
				FORAPythonUtil::exposeValueLikeCppmlTypeSimpleSerializers<ComputationSystemwideCpuAssignment>()
					.class_()
					.add_property(
							"cpusAssignedToChildren",
							&ComputationSystemwideCpuAssignment::cpusAssignedToChildren
							)
					.add_property(
							"cacheloadsAssignedToChildren",
							&ComputationSystemwideCpuAssignment::cacheloadsAssignedToChildren
							)
					.add_property(
							"cpusAssignedDirectly",
							&ComputationSystemwideCpuAssignment::cpusAssignedDirectly
							)
					.add_property(
							"cacheloadsAssignedDirectly",
							&ComputationSystemwideCpuAssignment::cacheloadsAssignedDirectly
							)
					.add_property(
							"totalBytesReferencedAtLastCheckpoint",
							&ComputationSystemwideCpuAssignment::totalBytesReferencedAtLastCheckpoint
							)
					;

			def("ComputationSystemwideCpuAssignment", cls);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputationSystemwideCpuAssignmentWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			ComputationSystemwideCpuAssignmentWrapper>::registerWrapper();




