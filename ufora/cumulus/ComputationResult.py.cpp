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
#include "ComputationResult.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../FORA/python/FORAPythonUtil.hppml"
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"

using namespace Cumulus;

class ComputationResultWrapper :
		public native::module::Exporter<ComputationResultWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "Cumulus";
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			object cls =
				FORAPythonUtil::exposeValueLikeCppmlType<ComputationResult>()
					.class_()
					.def("deserializedResult", &ComputationResult::deserializedResult)
					;

			def("ComputationResult", cls);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputationResultWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			ComputationResultWrapper>::registerWrapper();




