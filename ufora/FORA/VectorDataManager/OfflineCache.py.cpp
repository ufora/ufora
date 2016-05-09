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
#include "OfflineCache.hpp"

#include <stdint.h>
#include "../Serialization/SerializedObject.hpp"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/utilities.hpp"
using namespace Ufora::python;


namespace Cumulus {

class OfflineCacheWrapper :
		public native::module::Exporter<OfflineCacheWrapper> {
public:
		void	getDefinedTypes(std::vector<std::string>& outTypes)
			{
			outTypes.push_back(typeid(PolymorphicSharedPtr<OfflineCache>).name());
			}
		std::string		getModuleName(void)
			{
			return "Cumulus";
			}
		static boost::python::object extract(
								PolymorphicSharedPtr<OfflineCache>& cache,
								Fora::PageId inID
								)
			{
			PolymorphicSharedPtr<SerializedObject> tr;

				{
				ScopedPyThreads releaseTheGil;

				tr = cache->loadIfExists(inID);
				}

			if (tr)
				return boost::python::object(tr);

			return boost::python::object();
			}
		static void	store(PolymorphicSharedPtr<OfflineCache>& cache,
								Fora::PageId inID,
								const PolymorphicSharedPtr<SerializedObject>& inData
								)
			{
			ScopedPyThreads releaseTheGil;

			cache->store(inID, inData);
			}

		static bool	alreadyExists(
								PolymorphicSharedPtr<OfflineCache>& cache,
								Fora::PageId inID
								)
			{
			ScopedPyThreads releaseTheGil;

			return cache->alreadyExists(inID);
			}

		static uint64_t getCacheSizeUsedBytes(PolymorphicSharedPtr<OfflineCache>& cache)
			{
			ScopedPyThreads releaseTheGil;

			return cache->getCacheSizeUsedBytes();
			}

		static uint64_t getCacheItemCount(PolymorphicSharedPtr<OfflineCache>& cache)
			{
			ScopedPyThreads releaseTheGil;

			return cache->getCacheItemCount();
			}

		static uint64_t getCacheBytesDropped(PolymorphicSharedPtr<OfflineCache>& cache)
			{
			ScopedPyThreads releaseTheGil;

			return cache->getCacheBytesDropped();
			}

		static uint64_t getCacheItemsDropped(PolymorphicSharedPtr<OfflineCache>& cache)
			{
			ScopedPyThreads releaseTheGil;

			return cache->getCacheItemsDropped();
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<OfflineCache> >("OfflineCache", no_init)
				.def("store", &store)
				.def("alreadyExists", &alreadyExists)
				.def("loadIfExists", &extract)
				.add_property("cacheSizeUsedBytes", &getCacheSizeUsedBytes)
				.add_property("cacheItemCount", &getCacheItemCount)
				.add_property("cacheBytesDropped", &getCacheBytesDropped)
				.add_property("cacheItemsDropped", &getCacheItemsDropped)
				;
			}
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<Cumulus::OfflineCacheWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<Cumulus::OfflineCacheWrapper>::registerWrapper();

