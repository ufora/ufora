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
#include "RandomJOVGenerator.hppml"

#include <stdint.h>
#include <boost/python.hpp>

#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/ValueLikeCPPMLWrapper.hppml"
#include "../Core/ExecutionContext.hppml"

class RandomJOVGeneratorWrapper :
	public native::module::Exporter<RandomJOVGeneratorWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}

		static PolymorphicSharedPtr<RandomJOVGenerator>*
        makeClassBySeed(
                int seed,
                PolymorphicSharedPtr<Fora::Interpreter::ExecutionContext>& context
                )
			{
			return new PolymorphicSharedPtr<RandomJOVGenerator>(
                            new RandomJOVGenerator(seed, context)
                            );
			}

		static PolymorphicSharedPtr<RandomJOVGenerator>*
        makeClassByGenerator(
                boost::mt19937& generator,
                PolymorphicSharedPtr<Fora::Interpreter::ExecutionContext>& context
                )
			{
			return new PolymorphicSharedPtr<RandomJOVGenerator>(
                            new RandomJOVGenerator(generator, context)
                            );
			}

		static boost::python::object RJOVGRandomValue(
										PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
										const JOV& jov
									)
			{
			Nullable<ImplValContainer> r = rjovg->RandomValue(jov);
			if (!r) return boost::python::object();
			return boost::python::object(*r);
			}

		static boost::python::object RJOVTGRandomValue(
										PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
										const JOVT& jovt
									)
			{
			return RJOVGRandomValue(rjovg, JOV::Tuple(jovt));
			}

		static PolymorphicSharedPtr<RandomJOVGenerator>
        RJOVGSymbolStrings(
                PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
                boost::python::list symbolStringsList
                )
            {
			std::vector<std::string> symbol_strings;
			int length = boost::python::len(symbolStringsList);

			for (long k = 0; k < length; k++)
				{
				if (boost::python::extract<std::string>(symbolStringsList[k]).check())
					symbol_strings.push_back(boost::python::extract<std::string>(symbolStringsList[k])());
					else
					lassert(false);
				}
			rjovg->setSymbolStrings(symbol_strings);

			return rjovg;
			}

		static PolymorphicSharedPtr<RandomJOVGenerator> RJOVGsetMaxUnsignedInt(
														PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
														unsigned int i
														)
			{
			rjovg->setLikelyMaxUnsignedInt(i);
			return rjovg;
			}

		static PolymorphicSharedPtr<RandomJOVGenerator> RJOVGsetMaxReal(
														PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
														double d
														)
			{
			rjovg->setMaxReal(d);
			return rjovg;
			}

		static PolymorphicSharedPtr<RandomJOVGenerator> setMaxStringLength(
														PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
														int i
														)
			{
			rjovg->setMaxStringLength(i);
			return rjovg;
			}

		static PolymorphicSharedPtr<RandomJOVGenerator> RJOVGsetMinReal(
														PolymorphicSharedPtr<RandomJOVGenerator>& rjovg,
														double d
														)
			{
			rjovg->setMinReal(d);
			return rjovg;
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;

			class_<PolymorphicSharedPtr<RandomJOVGenerator> >("RandomJOVGenerator", no_init)
				.def("__init__", make_constructor(makeClassBySeed))
				.def("__init__", make_constructor(makeClassByGenerator))
				.def("symbolStrings", &RJOVGSymbolStrings)
				.def("randomValue", &RJOVGRandomValue)
				.def("randomValue", &RJOVTGRandomValue)
				.def("setMaxUnsignedInt", &RJOVGsetMaxUnsignedInt)
				.def("setMaxReal", &RJOVGsetMaxReal)
				.def("setMinReal", &RJOVGsetMinReal)
                .def("setMaxStringLength", &setMaxStringLength)
				;
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<RandomJOVGeneratorWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			RandomJOVGeneratorWrapper>::registerWrapper();

