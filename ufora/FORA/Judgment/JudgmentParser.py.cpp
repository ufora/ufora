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
#include "JudgmentParser.hppml"
#include "JudgmentOnValue.hppml"
#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"



class JudgmentParserWrapper :
		public native::module::Exporter<JudgmentParserWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}
			
		static JudgmentOnValueTuple parseJOVT(const string& inJOVString)
			{
			SimpleParseNode parseNode = parseStringToSimpleParse(inJOVString);
			
			return JudgmentParser::parseJOVT(parseNode);
			}
			
		static JudgmentOnValue parseJOV(const string& inJOVString)
			{
			SimpleParseNode parseNode = parseStringToSimpleParse(inJOVString);
			
			return JudgmentParser::parseJOV(parseNode);
			}
			
        static JudgmentOnResult parseJOR(const string& inJORString)
            {
			SimpleParseNode parseNode = parseStringToSimpleParse(inJORString);
			
			return JudgmentParser::parseJOR(parseNode);
			}
			
		static void jpeErrorTranslator(JudgmentParseError arg)
			{
			PyErr_SetString(
				PyExc_UserWarning,
				("JudgmentParseError: " + prettyPrintString(arg)).c_str()
				);
			}
			
		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			boost::python::register_exception_translator<JudgmentParseError>(&jpeErrorTranslator);
			
			def("parseStringToJOVT", &parseJOVT);
			def("parseStringToJOV", &parseJOV);
            def("parseStringToJOR", &parseJOR);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<JudgmentParserWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			JudgmentParserWrapper>::registerWrapper();

