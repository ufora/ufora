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
#include "MapWithIndex.py.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../python/CPPMLWrapper.hpp"
#include "../python/ScopedPyThreads.hpp"

class MapWithIndexWrapper :
	public native::module::Exporter<
			MapWithIndex<boost::python::object, boost::python::object>
			> {
public:
	std::string		getModuleName(void)
		{
		return "core";
		}
	void exportPythonWrapper()
		{
		using namespace boost::python;

		PythonWrapper<MapWithIndex<boost::python::object, boost::python::object> >
			::exportPythonInterface("MapWithIndex")
			;
		}

};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<MapWithIndexWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<
	MapWithIndexWrapper>::registerWrapper();

