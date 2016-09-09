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
#include "../../Vector/VectorDataID.hppml"
#include "VectorDataIDSlice.hppml"
#include "../../python/FORAPythonUtil.hppml"
#include "../../../core/python/ScopedPyThreads.hpp"
#include "../../../core/python/CPPMLWrapper.hpp"
#include "../../../native/Registrar.hpp"
#include "../../../core/containers/ImmutableTreeSet.py.hpp"

using TypedFora::Abi::VectorDataIDSlice;

class VectorDataIDSliceWrapper :
		public native::module::Exporter<VectorDataIDSliceWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}

		static VectorDataIDSlice createVectorDataIDSlice(VectorDataID& vdid, int64_t low, int64_t high)
			{
			return VectorDataIDSlice(vdid, IntegerSequence(high - low, low));
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;


			Ufora::python::CPPMLWrapper<VectorDataIDSlice>
					("VectorDataIDSlice", false).class_()
				.def("__str__", &FORAPythonUtil::scopedPrettyPrinter<VectorDataIDSlice>)
				.def("__repr__", &FORAPythonUtil::scopedPrettyPrinter<VectorDataIDSlice>)
				.def("__cmp__", &FORAPythonUtil::comparer<VectorDataIDSlice>)
				.def("__hash__", &FORAPythonUtil::hasher<VectorDataIDSlice>)
				;

			PythonWrapper<ImmutableTreeSet<VectorDataIDSlice> >::exportPythonInterface("VectorDataIDSlice");

			def("createVectorDataIDSlice", createVectorDataIDSlice);
			}
};
//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<VectorDataIDSliceWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<VectorDataIDSliceWrapper>::registerWrapper();

