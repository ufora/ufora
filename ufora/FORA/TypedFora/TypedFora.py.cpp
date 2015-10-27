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
#include "TypedFora.hppml"

#include <boost/python.hpp>
#include <boost/random.hpp>

#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../python/FORAPythonUtil.hppml"
#include "../../core/containers/ImmutableTreeVector.py.hpp"
#include "../Core/ClassMediator.hppml"
#include "../Native/NativeCode.hppml"

class TypedForaWrapper :
		public native::module::Exporter<TypedForaWrapper> {
public:
		std::string		getModuleName(void)
			{
			return "FORA";
			}
			
		static boost::python::object expressionType(const TypedFora::Expression& expr)
			{
			Nullable<TypedFora::Type> type = expr.type();
			if (!type)
				return boost::python::object();
			return boost::python::object(*type);
			}

		static TypedFora::Expression createGetItem(const TypedFora::Expression& expr, uword_t index)
			{
			return TypedFora::Expression::GetItem(expr, index);
			}

		static TypedFora::Expression createGetSlice(const TypedFora::Expression& expr, uword_t indexLow)
			{
			return TypedFora::Expression::GetSlice(expr, indexLow);
			}	

		static TypedFora::Expression createMakeTuple(
				const ImmutableTreeVector<TypedFora::MakeTupleArgument>& arguments
				)	
			{
			return TypedFora::Expression::MakeTuple(arguments);
			}

		void exportPythonWrapper()
			{
			using namespace boost::python;
			

			PythonWrapper<ImmutableTreeVector<TypedFora::Variable> >
				::exportPythonInterface("TypedFora::Variable");

			PythonWrapper<ImmutableTreeVector<TypedFora::MakeTupleArgument> >
				::exportPythonInterface("TypedFora::MakeTupleArgument");
				
			PythonWrapper<ImmutableTreeVector<TypedFora::Type> >
				::exportPythonInterface("TypedFora::Type");

			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::RefcountStyle>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::CallTarget>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::TransferTarget>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::Callable>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::Expression>(false)
				.class_()
				.def("type", &expressionType)
				.def("GetItem", &createGetItem)
				.def("GetSlice", &createGetSlice)
				.def("MakeTuple", &createMakeTuple)
				;
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::ContinuationFrame>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::Type>(false);
			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::Variable>(false)
				.class_()
				.def("Temp", TypedFora::Variable::Temp)
				.staticmethod("Temp")
				;

			FORAPythonUtil::exposeValueLikeCppmlType<TypedFora::InlineNativeOperationArg>(false);
			}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<TypedForaWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			TypedForaWrapper>::registerWrapper();


