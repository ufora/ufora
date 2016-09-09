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
#include "ExternalDatasetDescriptor.hppml"
#include "../python/FORAPythonUtil.hppml"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../native/Registrar.hpp"

class ExternalDatasetDescriptorWrapper :
		public native::module::Exporter<ExternalDatasetDescriptorWrapper> {
public:
		std::string getModuleName(void)
			{
			return "FORA";
			}

		static bool ExternalDatasetDescriptor_getstate_manages_dict(ExternalDatasetDescriptor& v)
			{
			return true;
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			FORAPythonUtil::exposeValueLikeCppmlType<ExternalDatasetDescriptor>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<OdbcRequest>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<S3Dataset>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<HttpRequest>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<FileDataset>(false);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ExternalDatasetDescriptorWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<ExternalDatasetDescriptorWrapper>::registerWrapper();

