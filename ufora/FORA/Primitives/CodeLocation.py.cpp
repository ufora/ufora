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
#include "CodeLocation.hppml"

#include <stdint.h>
#include "../../core/python/ValueLikeCPPMLWrapper.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/containers/ImmutableTreeVector.py.hpp"

class CodeLocationWrapper :
	public native::module::Exporter<CodeLocationWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}
	static CodeDefinitionPoint ExternalFromStringList(boost::python::object stringList)
		{
		return CodeDefinitionPoint::External(
			extractItvFromPythonList<string>(stringList)
			);
		}

	static boost::python::object getIDs(ForaStackTrace& trace)
		{
		return Ufora::python::containerWithBeginEndToList(trace.getStackTrace().elements());
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		Ufora::python::CPPMLWrapper<CodeDefinitionPoint>().class_()
			.def("__str__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<CodeDefinitionPoint>)
			.def("__repr__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<CodeDefinitionPoint>)
			.def("ExternalFromStringList", ExternalFromStringList)
			.staticmethod("ExternalFromStringList")
			;

		Ufora::python::CPPMLWrapper<CodeLocation>().class_()
			.def("__str__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<CodeLocation>)
			.def("__repr__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<CodeLocation>)
			.def("__hash__", &ValueLikeCPPMLWrapper::hasher<CodeLocation>)
			.def("__cmp__", &ValueLikeCPPMLWrapper::comparer<CodeLocation>)
			;

		Ufora::python::CPPMLWrapper<ForaStackTrace>().class_()
			.def("__str__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<ForaStackTrace>)
			.def("__repr__", ValueLikeCPPMLWrapper::scopedPrettyPrinter<ForaStackTrace>)
			.def("getIDs", getIDs)
			;

		PythonWrapper<ImmutableTreeVector<CodeLocation> >::exportPythonInterface("CodeLocation");
		}

};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<CodeLocationWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<
	CodeLocationWrapper>::registerWrapper();

