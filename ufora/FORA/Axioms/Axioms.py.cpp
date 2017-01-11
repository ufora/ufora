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
#include "Axioms.hppml"
#include "Axiom.hppml"

#include <stdint.h>
#include <vector>
#include <string>
#include "../../native/Registrar.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../Runtime.hppml"
#include "AxiomGroup.hppml"

#include <boost/python.hpp>

class AxiomsWrapper :
		public native::module::Exporter<AxiomsWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}
        static boost::python::object AxiomsGetAxiomByJOVT(
                    PolymorphicSharedPtr<Axioms>& axioms,
                    PolymorphicSharedPtr<TypedFora::Compiler>& r,
                    const JOVT& jovt
                )
            {
            Nullable<Axiom> axiom = axioms->axiom(*r, jovt);
            if (!axiom)
                return boost::python::object();
            return boost::python::object(*axiom);
            }

        static size_t AxiomsGetAxiomListSize(PolymorphicSharedPtr<Axioms>& a)
            {
            return a->interpreterAxioms().size();
            }

        static PolymorphicSharedPtr<AxiomGroup>
        AxiomsGetAxiomGroupByIndex(PolymorphicSharedPtr<Axioms>& a, int64_t ix)
            {
            if (ix < 0 || ix >= a->interpreterAxioms().size())
                throw std::out_of_range("");
            return a->interpreterAxioms()[ix].second;
            }

        static boost::python::object
        axiomSearchLinear(PolymorphicSharedPtr<Axioms>& a, const JudgmentOnValueTuple& s)
            {
            Nullable<uword_t> index = a->axiomSearchLinear(s);
            if (!index)
                return boost::python::object();
            return boost::python::object(*index);
            }

        static boost::python::object
        axiomSearchTree(PolymorphicSharedPtr<Axioms>& a, const JudgmentOnValueTuple& s)
            {
            Nullable<uword_t> index = a->axiomSearchTree(s);
            if (!index)
                return boost::python::object();
            return boost::python::object(*index);
            }

        static boost::python::object
        AxiomsGetCppWrapperCode(
                    PolymorphicSharedPtr<Axioms>& axioms
                    )
            {
            pair<std::string, std::string> code = axioms->getCppWrapperCode();

            return boost::python::make_tuple(code.first, code.second);
            }

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<Axioms> >("Axioms", no_init)
                .add_property("axiomCount", &AxiomsGetAxiomListSize)
                .def("__len__", &AxiomsGetAxiomListSize)
                .def("getAxiomByJOVT", &AxiomsGetAxiomByJOVT)
                .def("getAxiomGroupByIndex", &AxiomsGetAxiomGroupByIndex)
                .def("__getitem__", &AxiomsGetAxiomGroupByIndex)
                .def("axiomSearchLinear", &axiomSearchLinear)
                .def("axiomSearchTree", &axiomSearchTree)
                .def("getCppWrapperCode", &AxiomsGetCppWrapperCode)
                ;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<AxiomsWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			AxiomsWrapper>::registerWrapper();

