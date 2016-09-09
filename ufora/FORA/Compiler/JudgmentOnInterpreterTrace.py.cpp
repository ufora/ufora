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
#include "../python/FORAPythonUtil.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"

/*
class JudgmentOnInterpreterTraceWrapper :
		public native::module::Exporter<JudgmentOnInterpreterTraceWrapper> {
public:
		std::string	     getModuleName(void)
			{
			return "FORA";
			}

		static boost::python::object reasonForward(
							boost::python::object pyTerms
							)
			{
			ImmutableTreeVector<Fora::InterpreterTraceTerm> terms;

			Ufora::python::toCPP(pyTerms, terms);

			Fora::JudgmentOnInterpreterTrace::Path path;

			for (long k = 0; k < terms.size(); k++)
				path.addTraceTerm(terms[k]);

			return Ufora::python::containerWithBeginEndToList(path.forward());
			}

		static boost::python::object reasonBackward(
							PolymorphicSharedPtr<Axioms> inAxioms,
							PolymorphicSharedPtr<TypedFora::Compiler> inCompiler,
							boost::python::object pyTerms
							)
			{
			ImmutableTreeVector<Fora::JudgmentOnInterpreterTrace::Term> terms;

			Ufora::python::toCPP(pyTerms, terms);

			Fora::JudgmentOnInterpreterTrace::Path path;

			for (long k = 0; k < terms.size(); k++)
				path.addForwardTerm(terms[k]);

			path.updateBackwardSet(inAxioms, inCompiler);

			return Ufora::python::containerWithBeginEndToList(path.backward());
			}

		static Fora::JudgmentOnInterpreterTrace::Term withFinalResultOf(
								Fora::JudgmentOnInterpreterTrace::Term& term,
								JOV& jov
								)
			{
			Fora::JudgmentOnInterpreterTrace::Term tr = term;

			tr.result()->value() = jov;

			return tr;
			}

		static ImmutableTreeVector<JOV> getJovsAsITV(
								Fora::JudgmentOnInterpreterTrace::Term& term
								)
			{
			return term.jovs();
			}

		static ControlFlowGraphJumpPoint getLocation(
								Fora::JudgmentOnInterpreterTrace::Term& term
								)
			{
			return term.location();
			}


		static boost::python::object getJovs(
								Fora::JudgmentOnInterpreterTrace::Term& term
								)
			{
			return Ufora::python::containerWithBeginEndToList(term.jovs());
			}

		static long getHeight(Fora::JudgmentOnInterpreterTrace::Term& term)
			{
			return term.currentStack().size();
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			FORAPythonUtil::exposeValueLikeCppmlType<Fora::JudgmentOnInterpreterTrace::Term>()
				.class_()
				.def("withFinalResultOf", withFinalResultOf)
				.def("getJovs", getJovs)
				.def("getJovsAsITV", &getJovsAsITV)
				.def("getLocation", &getLocation)
				.def("isEmpty", &Fora::JudgmentOnInterpreterTrace::Term::isEmpty)
				.def("getHeight", &getHeight)
				;

			FORAPythonUtil::exposeValueLikeCppmlType<Fora::JudgmentOnInterpreterTrace::Stackframe>();
			FORAPythonUtil::exposeValueLikeCppmlType<Fora::JudgmentOnInterpreterTrace::Result>();

			def("reasonForward", &reasonForward);
			def("reasonBackward", &reasonBackward);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<JudgmentOnInterpreterTraceWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			JudgmentOnInterpreterTraceWrapper>::registerWrapper();


*/



