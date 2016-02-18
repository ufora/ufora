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
#include "Function.hppml"

#include <stdint.h>
#include "../python/FORAPythonUtil.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "Parser.hppml"
#include "../Core/ClassMediator.hppml"
#include "../ControlFlowGraph/ControlFlowGraph.hppml"
#include "../Core/Type.hppml"

#include "VariableAllocator.hppml"
#include "FunctionToCFG.hppml"
#include "FunctionStage1.hppml"
#include "FunctionStage2.hppml"
#include "FunctionStage2Converter.hppml"
#include "FunctionStage3.hppml"

class FunctionWrapper :
		public native::module::Exporter<FunctionWrapper> {
public:
		std::string		 getModuleName(void)
			{
			return "FORA";
			}
			
		static uword_t functionLen(const Function& inFunction)
			{
			if (inFunction.isEmpty())
				return 0;
			return inFunction.getTerm().pattern().size();
			}

		static string functionGetItem(const Function& inFunction, int32_t ix)
			{
			lassert(ix >= 0 && ix < functionLen(inFunction));

			TuplePatternElement p = inFunction.getTerm().pattern()[ix];

			if (p.isNormal() //&& p.getNormal().match().pattern().isAnything()
						&& p.getNormal().match().name())
				return p.getNormal().match().name()->toString();

			if (p.isVarArgs() && p.getVarArgs().varname())
				return "*" + p.getVarArgs().varname()->toString();

			return "";
			}

        static string functionGetArgPrefix(const Function& inFunction, int32_t ix)
            {
			lassert(ix >= 0 && ix < functionLen(inFunction));

			TuplePatternElement p = inFunction.getTerm().pattern()[ix];

			if (p.isNormal()) //&& p.getNormal().match().pattern().isAnything()
                if (p.getNormal().match().pattern().isConstant() && 
                		p.getNormal().match().pattern().getConstant().value().isConstant())
                    return p.getNormal().match().pattern().getConstant().value().getConstant().val().toString();

			return "";
            }

		template<class T>
		static std::string	scopedPrettyPrinter(const T& in)
			{
			ScopedPyThreads threads;
			return prettyPrintString(in);
			}
		
		static void fpeErrorTranslator(FunctionParseError arg)
			{
			PyErr_SetString(PyExc_UserWarning, ("FunctionParseError: " + prettyPrintString(arg)).c_str());
			}

		static ControlFlowGraph functionToCFGBasic(Function f, int argCount)
			{
			Fora::Language::FunctionToCFG& converter =
					Runtime::getRuntime().getFunctionToCFGConverter();

			return converter.functionToCFG(
					CPPMLOpaqueHandle<Function>(new Function(f)),
					ClassMediatorResumption::Entry(),
					ApplySignature(argCount)
					);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			
			Ufora::python::CPPMLWrapper<Function>(true).class_()
				.def("__str__", &FORAPythonUtil::scopedPrettyPrinter<Function>)
				.def("__len__", &functionLen)
				.def("__getitem__", &functionGetItem)
				.add_property("hash", &FORAPythonUtil::scopedHashValue<Function>)
				.def("__hash__", &FORAPythonUtil::hasher<Function>)
				.def("__cmp__", &FORAPythonUtil::comparer<Function>)
                .def("getItemPrefix", &functionGetArgPrefix)
				.def("toCFG", &functionToCFGBasic)
				.enable_pickling()
				;

			Ufora::python::CPPMLWrapper<FunctionParseError>().class_()
				.def("__str__", scopedPrettyPrinter<FunctionParseError>)
				.enable_pickling()
				;

			boost::python::register_exception_translator<FunctionParseError>(&fpeErrorTranslator);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<FunctionWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			FunctionWrapper>::registerWrapper();






