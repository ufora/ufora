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
//can be called into by FORACodeFormatter.py

#include "FORAValuePrinter.hppml"
#include "../Language/ParserExpressions.hppml"
#include <stdint.h>
#include <string>
#include "../python/FORAPythonUtil.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/SimpleParse/SimpleParse.hppml"

class FORACodeFormatter : public native::module::Exporter<FORACodeFormatter>
	{
	std::string getModuleName(void)
		{
		return "FORACodeFormatter";
		}

	static std::string formatTextAsCode(std::string inText)
		{
		SimpleParseNode stage1 = parseStringToSimpleParse(inText);
		ParserExpressions parser(true, CodeDefinitionPoint(), "");

		//allow empty expression
		Expression stage2 = parser.parseToExpression(stage1, true);

		std::ostringstream s;
			{
			CPPMLPrettyPrintStream st(s);
			FORAValuePrinting::FORAValuePrinter printer(st);
			printer.toString(stage2);
			}

		return s.str();
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		def("formatTextAsCode", &formatTextAsCode);
		}
	};

template<>
char native::module::Exporter<FORACodeFormatter>::mEnforceRegistration
	= native::module::ExportRegistrar<FORACodeFormatter>::registerWrapper();

