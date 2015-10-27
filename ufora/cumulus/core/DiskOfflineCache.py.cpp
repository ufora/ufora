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
#include "DiskOfflineCache.hpp"
#include "../../FORA/VectorDataManager/OfflineCache.hpp"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/threading/CallbackScheduler.hppml"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
using namespace Ufora::python;


namespace Cumulus {


class DiskOfflineCacheWrapper :
		public native::module::Exporter<DiskOfflineCacheWrapper> {
public:
		void	getDefinedTypes(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(DiskOfflineCache::pointer_type).name());
			}
		void dependencies(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(OfflineCache::pointer_type).name());				
			}
		std::string		getModuleName(void)
			{
			return "Cumulus";
			}
		static DiskOfflineCache::pointer_type* Init(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				std::string basePath, 
				uword_t maxCacheSize, 
				uword_t maxCacheItemCount
				)
			{
			return new DiskOfflineCache::pointer_type(
				new DiskOfflineCache(
					inCallbackScheduler,
					basePath,
					maxCacheSize,
					maxCacheItemCount
					)
				);
			}
		
		static uword_t getTotalBytesLoaded(DiskOfflineCache::pointer_type cache)
			{
			return cache->getTotalBytesLoaded();
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			class_<DiskOfflineCache::pointer_type,
					boost::python::bases<OfflineCache::pointer_type>
				>("DiskOfflineCache", no_init)
				.def("__init__", make_constructor(Init))
				.add_property("totalBytesLoaded", &getTotalBytesLoaded)
				;
			}
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<Cumulus::DiskOfflineCacheWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<Cumulus::DiskOfflineCacheWrapper>::registerWrapper();

