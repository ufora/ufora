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
#include "module.hpp"
#include <boost/python.hpp>
#include "Registrar.hpp"

#include <string>

using namespace std;

namespace native {
namespace module {

	boost::python::scope createModule(const std::string& inModuleName) {

		boost::python::object thePackage = boost::python::scope();

		std::string currentPackageName =
			boost::python::extract<string>(thePackage.attr("__name__"))();

		boost::python::object module(
			boost::python::handle<>(boost::python::borrowed(
				PyImport_AddModule((currentPackageName + "." + inModuleName).c_str())
			))
		);

		thePackage.attr(inModuleName.c_str()) = module;

		// I think this is required to get pickling to work
        module.attr("__path__") = currentPackageName + "." + inModuleName;

		return boost::python::scope(module);
	}
}
}

