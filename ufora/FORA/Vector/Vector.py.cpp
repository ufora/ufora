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
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/ValueLikeCPPMLWrapper.hppml"
#include "VectorDataID.hppml"
#include "VectorUtilities.hpp"
#include "../VectorDataManager/VectorDataManager.hppml"
#include "../TypedFora/ABI/VectorDataIDSlice.hppml"
#include "../Core/MemoryPool.hpp"
#include "../Core/ImplVal.hppml"
#include "../Core/ImplValContainer.hppml"

class VectorWrapper :
		public native::module::Exporter<VectorWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}

		static ImplValContainer    createFORAFreeBinaryVectorStatic(
				                        const VectorDataID& inID,
				                        uword_t nElements,
				                        PolymorphicSharedPtr<VectorDataManager> inVDM
				                        )
			{
			return createFORAFreeBinaryVector(
				inID,
				nElements,
				MemoryPool::getFreeStorePool(),
				&*inVDM
				);
			}

		static ImplValContainer    createFORAFreeBinaryVectorFromSlicesStatic(
				                        boost::python::object pyVectorDataIDslices,
				                        PolymorphicSharedPtr<VectorDataManager> inVDM
				                        )
			{
			ImmutableTreeVector<TypedFora::Abi::VectorDataIDSlice> vectorDataIDSlices;

			Ufora::python::toCPP(pyVectorDataIDslices, vectorDataIDSlices);

			return createFORAFreeBinaryVectorFromSlices(
				vectorDataIDSlices,
				MemoryPool::getFreeStorePool(),
				&*inVDM
				);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			def("createFORAFreeBinaryVector", createFORAFreeBinaryVector);
			def("createFORAFreeBinaryVector", createFORAFreeBinaryVectorStatic);
			def("createFORAFreeBinaryVectorFromSlices", createFORAFreeBinaryVectorFromSlicesStatic);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<VectorWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			VectorWrapper>::registerWrapper();

