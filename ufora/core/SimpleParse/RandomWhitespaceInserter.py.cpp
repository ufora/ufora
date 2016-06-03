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
#include "RandomWhitespaceInserter.hppml"

#include <boost/python.hpp>

#include "../../native/Registrar.hpp"
#include "../python/utilities.hpp"
#include "../../FORA/python/FORAPythonUtil.hppml"

class RandomWhitespaceInserterWrapper :
    public native::module::Exporter<RandomWhitespaceInserterWrapper> {
public:
    std::string getModuleName()
        {
        return "FORA";
        }

    static PolymorphicSharedPtr<RandomWhitespaceInserter>*
    makeClassBySeed(int64_t seed)
        {
        return new PolymorphicSharedPtr<RandomWhitespaceInserter>(
            new RandomWhitespaceInserter(seed)
            );
        }

    static std::string stringifyWithRandomWhitespaceAndComments(
            PolymorphicSharedPtr<RandomWhitespaceInserter> whitespaceInserter,
            const SimpleParseNode& node
            )
        {
        return whitespaceInserter->stringifyWithRandomWhitespaceAndComments(node);
        }

    static void seed(
            PolymorphicSharedPtr<RandomWhitespaceInserter> whitespaceInserter,
            int64_t seed
            )
        {
        whitespaceInserter->seed(seed);
        }

    void exportPythonWrapper()
        {
        using namespace boost::python;

        class_<PolymorphicSharedPtr<RandomWhitespaceInserter> >(
        "RandomWhitespaceInserter", no_init)
            .def("__init__", make_constructor(makeClassBySeed))
            .def("stringifyWithRandomWhitespaceAndComments",
                &stringifyWithRandomWhitespaceAndComments)
            .def("seed", &seed)
            ;
        }

    };

template<>
char native::module::Exporter<RandomWhitespaceInserterWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			RandomWhitespaceInserterWrapper>::registerWrapper();


