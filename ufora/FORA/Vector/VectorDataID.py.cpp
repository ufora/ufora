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
#include "VectorDataID.hppml"
#include "../python/FORAPythonUtil.hppml"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../native/Registrar.hpp"
#include "../../core/containers/ImmutableTreeSet.py.hpp"

class VectorDataIDWrapper :
		public native::module::Exporter<VectorDataIDWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}
			
		static bool VectorDataID_getstate_manages_dict(VectorDataID& v)
			{
			return true;
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			Ufora::python::CPPMLWrapper<VectorDataID>
					("VectorDataID", false).class_()
				.def("__str__", &FORAPythonUtil::scopedPrettyPrinter<VectorDataID>)
				.def("__repr__", &FORAPythonUtil::scopedPrettyPrinter<VectorDataID>)
				.def("__cmp__", &FORAPythonUtil::comparer<VectorDataID>)
				.def("__hash__", &FORAPythonUtil::hasher<VectorDataID>)
				.def("__getstate__", &FORAPythonUtil::serializer<VectorDataID>)
				.def("__setstate__", &FORAPythonUtil::deserializer<VectorDataID>)
				.def("__getstate_manages_dict__", &VectorDataID_getstate_manages_dict)
				.add_property("page", &VectorDataID::getPage)
				.enable_pickling()
				;

			PythonWrapper<ImmutableTreeSet<VectorDataID> >::exportPythonInterface("VectorDataID");
			}
};
//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<VectorDataIDWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<VectorDataIDWrapper>::registerWrapper();

