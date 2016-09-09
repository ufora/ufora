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
#include "ComputationPriority.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../FORA/python/FORAPythonUtil.hppml"
#include "../native/Registrar.hpp"
#include "../core/python/CPPMLWrapper.hpp"

using namespace Cumulus;

class ComputationPriorityWrapper :
		public native::module::Exporter<ComputationPriorityWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "Cumulus";
			}

		static ComputationPriority makeCompPriorityFromInt(int x)
			{
			return ComputationPriority(null() << uint64_t(x));
			}

		static ComputationPriority makeCompPriorityFromTwoInts(int x, int y)
			{
			return ComputationPriority(null() << uint64_t(x), y);
			}

		static ComputationPriority makeCompPriorityFromEmpty()
			{
			return ComputationPriority();
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			object cls =
				FORAPythonUtil::exposeValueLikeCppmlTypeSimpleSerializers<ComputationPriority>()
					.class_()
					.def("withPrioritySource", &ComputationPriority::withPrioritySource)
					;

			def("ComputationPriority", cls);

			def("ComputationPriority", makeCompPriorityFromInt);
			def("ComputationPriority", makeCompPriorityFromTwoInts);
			def("ComputationPriority", makeCompPriorityFromEmpty);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputationPriorityWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			ComputationPriorityWrapper>::registerWrapper();




