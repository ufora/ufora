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
#include "TypedJumpTarget.hppml"
#include "../TypedFora.hppml"

#include "Compiler.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../../native/Registrar.hpp"
#include "../../../core/python/ScopedPyThreads.hpp"
#include "../../../core/python/CPPMLWrapper.hpp"

#include "../../../core/python/utilities.hpp"
using namespace Ufora::python;

class TypedForaCompilerWrapper :
		public native::module::Exporter<TypedForaCompilerWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}

		static TypedFora::TypedJumpTarget compile(
							PolymorphicSharedPtr<TypedFora::Compiler>& r,
							const TypedFora::Callable& inGraph,
							const std::string& axiomName
							)
			{
			return r->compile(inGraph, axiomName);
			}

		static bool anyCompilingOrPending(PolymorphicSharedPtr<TypedFora::Compiler>& c)
			{
			return c->anyCompilingOrPending();
			}

		static TypedFora::TypedJumpTarget compileUnnamed(
							PolymorphicSharedPtr<TypedFora::Compiler>& r,
							const TypedFora::Callable& inGraph
							)
			{
			uword_t index = 0;
			while (r->isDefined("AnonymousFunction_" + boost::lexical_cast<string>(index)))
				index++;

			return r->compile(inGraph, "AnonymousFunction_" + boost::lexical_cast<string>(index));
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<TypedFora::Compiler> >("TypedFora::Compiler", no_init)
				.def("compile", &compile)
				.def("compile", &compileUnnamed)
				.def("anyCompilingOrPending", anyCompilingOrPending)
				;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<TypedForaCompilerWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			TypedForaCompilerWrapper>::registerWrapper();

