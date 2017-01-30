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
#include "CSTValue.hppml"

#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ValueLikeCPPMLWrapper.hppml"

class CSTValueWrapper :
	public native::module::Exporter<CSTValueWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}
	static std::string CSTValueToString(CSTValue& v)
		{
		return v.toString();
		}
	static ImplValContainer CSTValueGetIVC(CSTValue& v)
		{
		return ImplValContainer(v.getReference());
		}
	static hash_type CSTValueHash(CSTValue& v)
		{
		return v.hash();
		}
	static CSTValue* constructFromCSTValue(CSTValue& v)
		{
		return new CSTValue(v);
		}
	static CSTValue* constructFromNothing()
		{
		return new CSTValue();
		}
	void exportPythonWrapper()
		{
		using namespace boost::python;

		class_<CSTValue>("CSTValue", init<ImplValContainer>())
			.def("__init__", make_constructor(constructFromCSTValue))
			.def("__init__", make_constructor(constructFromNothing))
			.def("__str__", &CSTValueToString)
			.def("__repr__", &CSTValueToString)
			.add_property("hash", &CSTValueHash)
			.def("getIVC", &CSTValueGetIVC)
			;
		}

};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<CSTValueWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<
	CSTValueWrapper>::registerWrapper();

