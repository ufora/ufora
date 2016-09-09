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
#include "Function.hppml"

#include <stdint.h>
#include "../python/FORAPythonUtil.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"

#include "FunctionToCFG.hppml"

#include "../Core/ClassMediator.hppml"

class ObjectDefinitionWrapper :
		public native::module::Exporter<ObjectDefinitionWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "FORA";
			}

		static ControlFlowGraph objectDefinitionToCFGBasic(
										ObjectDefinition& objectDefinition,
										int argCount
										)
			{
			Fora::Language::FunctionToCFG& converter
					= Runtime::getRuntime().getFunctionToCFGConverter();

			return converter.functionToCFG(
					ClassMediator::Object("", objectDefinition, LexicalBindingMap(), CSTValue()),
					ClassMediatorResumption::Entry(),
					ApplySignature(argCount)
					);
			}

		static int32_t termCount(ObjectDefinition& definition)
			{
			ObjectDefinitionBody body = definition.body();
			int32_t tr = 0;

			while (body.isTerm())
				{
				tr++;
				body = body.getTerm().otherwise();
				}

			return tr;
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<ObjectDefinition>("ObjectDefinition", init<>())
				.def("__str__", FORAPythonUtil::scopedPrettyPrinter<ObjectDefinition>)
				.def("toCFG", &objectDefinitionToCFGBasic)
				.def("termCount", termCount,
					"Count how many terms there are in the object definition.")
				;

			Ufora::python::CPPMLWrapper<ObjectDefinitionTermWithMetadata>(true).class_()
				;

			Ufora::python::CPPMLWrapper<ClassDefinitionTermWithMetadata>(true).class_()
				;

			Ufora::python::CPPMLWrapper<ObjectDefinitionTerm>(true).class_()
				;

			Ufora::python::CPPMLWrapper<ClassDefinitionTerm>(true).class_()
				;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ObjectDefinitionWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			ObjectDefinitionWrapper>::registerWrapper();






