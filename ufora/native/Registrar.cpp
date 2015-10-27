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
#include "Registrar.hpp"
#include "module.hpp"
#include "../core/lassert.hpp"

namespace native {
namespace module {

Registry& 	Registry::getRegistry()
	{
	static Registry r;
	return r;
	}

//add a registrar to the global registry
void	Registry::addRegistrar(boost::shared_ptr<ExporterBase> inRegistrar)
	{
	mRegistrars[inRegistrar->getModuleName()].push_back(inRegistrar);
	
	std::vector<std::string> defined;
	inRegistrar->getDefinedTypes(defined);
	for (long k = 0; k < defined.size();k++)
		mExportersByTypeInfo[defined[k]] = inRegistrar;
	}
void 	Registry::callRegistrar(boost::shared_ptr<ExporterBase> inRegistrar)
	{
	if (mRegistrarsCalled.find(inRegistrar) != mRegistrarsCalled.end())
		return;
	
	std::vector<std::string> deps;
	inRegistrar->dependencies(deps);
	
	for (long k = 0; k < deps.size();k++)
		{
		lassert_dump(mExportersByTypeInfo[deps[k]], "no exporter for " << deps[k]);
		callRegistrar(mExportersByTypeInfo[deps[k]]);
		}
	
	mRegistrarsCalled.insert(inRegistrar);
	
	
	boost::python::scope scope(createModule(inRegistrar->getModuleName()));
	inRegistrar->exportPythonWrapper();
	}
void	Registry::callAllRegistrars(void)
	{
	boost::python::scope scope(boost::python::import("ufora.native"));
	
	for (std::map<std::string,
				std::vector<boost::shared_ptr<ExporterBase> > >::iterator
			it = mRegistrars.begin(),
			it_end = mRegistrars.end();
			it != it_end;
			++it)
		{
		for (long k = 0; k < it->second.size();k++)
			callRegistrar(it->second[k]);
		}
	}

}
}


