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
#include <boost/python.hpp>
#include "NoncontiguousByteBlock.hpp"


#include "../../native/Registrar.hpp"
#include "../python/ScopedPyThreads.hpp"
#include "../python/CPPMLWrapper.hpp"
#include "../containers/ImmutableTreeVector.py.hpp"
#include "../threading/ScopedThreadLocalContext.hpp"

class NoncontiguousByteBlockWrapper :
		public native::module::Exporter<NoncontiguousByteBlockWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}
		static PolymorphicSharedPtr<NoncontiguousByteBlock>*
		constructNoncontiguousByteBlock(std::string inString)
			{
			return new PolymorphicSharedPtr<NoncontiguousByteBlock>(
				new NoncontiguousByteBlock(std::move(inString))
				);
			}

		static std::string toString(PolymorphicSharedPtr<NoncontiguousByteBlock> block)
			{
			return block->toString();
			}

		static uword_t totalByteCount(PolymorphicSharedPtr<NoncontiguousByteBlock> block)
			{
			return block->totalByteCount();
			}


		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<NoncontiguousByteBlock> >("NoncontiguousByteBlock", no_init)
				.def("__init__", make_constructor(constructNoncontiguousByteBlock))
				.def("toString", toString)
				.def("__len__", totalByteCount)
				;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<NoncontiguousByteBlockWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<NoncontiguousByteBlockWrapper>::registerWrapper();

