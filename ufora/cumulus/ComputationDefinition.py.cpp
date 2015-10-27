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
#include "ComputationDefinition.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../FORA/python/FORAPythonUtil.hppml"
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"
#include "../core/python/utilities.hpp"
#include "../core/containers/ImmutableTreeVector.py.hpp"
using namespace Cumulus;

class ComputationDefinitionWrapper :
		public native::module::Exporter<ComputationDefinitionWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "Cumulus";
			}

		static ComputationDefinition* computationDefinitionFromIVC(ImplValContainer& val)
			{
			return new ComputationDefinition(
				ComputationDefinition::Root(
					ComputationDefinitionTerm::ApplyFromTuple(val)
					)
				);
			}

		static hash_type ComputationDefinitionHash(ComputationDefinition def)
			{
			return def.hash();
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			boost::python::object compDefCls = 
				FORAPythonUtil::exposeValueLikeCppmlType<ComputationDefinition>()
					.class_()
					.def("__init__", make_constructor(computationDefinitionFromIVC))
					.def("hash", &ComputationDefinitionHash)
				;
			def("ComputationDefinition", compDefCls);

			boost::python::object compDefTermCls = 
				FORAPythonUtil::exposeValueLikeCppmlType<ComputationDefinitionTerm>()
					.class_();

			def("ComputationDefinitionTerm", compDefTermCls);

			PythonWrapper<ImmutableTreeVector<ComputationDefinitionTerm> >
				::exportPythonInterface("ComputationDefinitionTerm");

			}


};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputationDefinitionWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			ComputationDefinitionWrapper>::registerWrapper();




