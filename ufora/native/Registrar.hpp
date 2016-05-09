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
#ifndef native_Registrar_hpp
#define native_Registrar_hpp

#include <vector>
#include <map>
#include <set>
#include <boost/shared_ptr.hpp>
#include <iostream>
#include <vector>
#include <string>

/***************
Classes to support auto-registration of python wrappers

We define a registrar class, of which there is a single, globally available
instance.  Global instances of 'Registrar<T>' register the python
wrapper with the main factory.

****************/

namespace native {
namespace module {

class ExporterBase {
public:
		ExporterBase()
			{
			}
		virtual void exportPythonWrapper() = 0;
		virtual std::string		getModuleName(void)  = 0;

		//should return a list of typenames you define. may be empty if
		//nobody else depends on those.
		virtual void	getDefinedTypes(std::vector<std::string>& outTypes) {};

		virtual void 	dependencies(std::vector<std::string>& outDeps) {};
private:
		std::string 	mModuleName;
};

//abstract base class to export python types at module load time
template<class DerivedType>
class Exporter : public ExporterBase {
public:
		Exporter()
			{
			}
private:
		static char mEnforceRegistration;
};


class Registry {
public:
		Registry() {}
		~Registry() {}

		static Registry& 	getRegistry();

		//add a registrar to the global registry
		void	addRegistrar(boost::shared_ptr<ExporterBase> inRegistrar);

		void	callAllRegistrars(void);

		void	callRegistrar(boost::shared_ptr<ExporterBase> exporter);
private:
		std::map<std::string,
			std::vector<
				boost::shared_ptr<ExporterBase>
				>
			>											mRegistrars;
		std::set<boost::shared_ptr<ExporterBase> >		mRegistrarsCalled;
		std::map<std::string, boost::shared_ptr<ExporterBase> > mExportersByTypeInfo;
};

template<typename ExporterType>
class ExportRegistrar {
public:
		static char registerWrapper()
			{
			Registry::getRegistry().addRegistrar(
				boost::shared_ptr<ExporterBase>(
					new ExporterType()
					)
				);
			return 0;
			}

		static char registerWrapper(std::string arg)
			{
			Registry::getRegistry().addRegistrar(
				boost::shared_ptr<ExporterBase>(
					new ExporterType(arg)
					)
				);
			return 0;
			}
};



};
};

#endif

