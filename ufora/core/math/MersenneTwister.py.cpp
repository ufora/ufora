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
#include <boost/random/mersenne_twister.hpp>

#include "../../native/Registrar.hpp"
#include "../python/CPPMLWrapper.hpp"
#include "../python/ScopedPyThreads.hpp"


/*
    A wrapper for the boost Mersenne Twister random number generator.
    Called by JudgmentOnValueRandom.hppml
*/

namespace Ufora {


class MersenneTwisterWrapper:
    public native::module::Exporter<MersenneTwisterWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "MersenneTwister";
			}

        static boost::shared_ptr<boost::mt19937>
        makeClass(const int& seed = 5489)
            {
            return boost::shared_ptr<boost::mt19937>(new boost::mt19937(seed));
            }

		void exportPythonWrapper()
			{
			using namespace boost::python;

            class_<boost::mt19937, boost::shared_ptr<boost::mt19937> >
                ("MersenneTwister")
                .def("__init__", make_constructor(makeClass));
                ;
            }
};

}

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<
	Ufora::MersenneTwisterWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			Ufora::MersenneTwisterWrapper>::registerWrapper();

