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
#pragma once

#include <stdint.h>
#include <boost/python.hpp>
#include <string>
#include "RandomGenerator.hppml"
#include "../../core/math/Hash.hpp"


template<class T>
class PythonWrapper;

template<>
class PythonWrapper<RandomGenerator>	{
public:
		static std::string hash_str(Hash& inHash)
			{
			return "Hash(" + hashToString(inHash) + ")";
			}
		static void exportPythonInterface()
			{
			using namespace boost::python;

			class_<RandomGenerator, boost::shared_ptr<RandomGenerator> >("RandomGenerator", init<std::string>())
				.def("__str__", &RandomGenerator::to_string)
				.def("rand", &RandomGenerator::rand)
				.def("newGenerator", &RandomGenerator::newGenerator)
				;
			}
};


