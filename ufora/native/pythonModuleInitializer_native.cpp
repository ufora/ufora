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


BOOST_PYTHON_MODULE(native)
{
    using native::module::createModule;
	boost::python::object thePackage = boost::python::scope();
	thePackage.attr("__path__") = "ufora.native";

	native::module::Registry::getRegistry().callAllRegistrars();
}


