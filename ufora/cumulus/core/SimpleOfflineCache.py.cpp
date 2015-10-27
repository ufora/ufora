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
#include "SimpleOfflineCache.hpp"

#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
using namespace Ufora::python;


namespace Cumulus {

class CacheWrapper;

class SimpleOfflineCacheWrapper :
		public native::module::Exporter<SimpleOfflineCacheWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "Cumulus";
			}
		void dependencies(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(OfflineCache::pointer_type).name());
			}
		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			class_<SimpleOfflineCache::pointer_type,
					boost::python::bases<OfflineCache::pointer_type >
				>("SimpleOfflineCache", no_init)
				.def("__init__", 
						make_constructor(
							SimpleOfflineCache::pointer_type::Constructor2<PolymorphicSharedPtr<CallbackScheduler>, uword_t>
							)
						)
				.def("dropCacheTerm", &SimpleOfflineCache::dropCacheTermStatic)
				.add_property("totalBytes", &SimpleOfflineCache::totalBytesStatic)
				.add_property("totalBytesLoaded", &SimpleOfflineCache::totalBytesLoadedStatic)
				;
			}
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<Cumulus::SimpleOfflineCacheWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<Cumulus::SimpleOfflineCacheWrapper>::registerWrapper();


