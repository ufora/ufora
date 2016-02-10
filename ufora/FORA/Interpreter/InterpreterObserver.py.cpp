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
#include "../python/FORAPythonUtil.hppml"
#include "../Interpreter/InterpreterObserver.hppml"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/utilities.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../../native/Registrar.hpp"

#include "../../core/serialization/OFileProtocol.hpp"
#include "../../FORA/Serialization/SerializedObjectFlattener.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/threading/SimpleCallbackSchedulerFactory.hppml"

#include "../../core/PolymorphicSharedPtrBinder.hpp"
#include "../../core/PolymorphicSharedPtrFuncFromMemberFunc.hpp"
#include "../../core/serialization/IFileProtocol.hpp"

using namespace Ufora::python;

using namespace Fora::Interpreter;
using namespace Fora::Compiler;

class InterpreterObserverWrapper :
	public native::module::Exporter<InterpreterObserverWrapper> {
public:
	void dependencies(std::vector<std::string>& outTypes)
		{
		outTypes.push_back(typeid(Runtime).name());
		}

	std::string		getModuleName(void)
		{
		return "FORA";
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<PolymorphicSharedPtr<InterpreterObserver> >("InterpreterObserver", no_init)
			;
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<InterpreterObserverWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<InterpreterObserverWrapper>::registerWrapper();

