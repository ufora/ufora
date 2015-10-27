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
#ifndef SimplParse_py_hpp
#define SimplParse_py_hpp

#include <boost/python.hpp>
#include <string>
#include "SimpleParse.hppml"
#include "../../core/serialization/Serialization.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../../core/cppml/CPPMLEquality.hppml"
#include "../../core/serialization/Serialization.hpp"
#include "../../core/containers/ImmutableTreeVector.py.hpp"

template<class T>
class PythonWrapper;

template<>
class PythonWrapper<SimpleParseNode>{
public:
		template<class T>
		static int cppmlCmpPy(const T& l, boost::python::object& other)
			{
			boost::python::extract<T> extractor(other);

			if (!extractor.check())
				return -1;

			return cppmlCmp(l,extractor());
			}

		template<class T>
		static boost::python::class_<T> defineSimpleCPPMLClass(string name)
			{
			using namespace boost::python;

			Ufora::python::CPPMLWrapper<T> T_;
						T_.class_()
							.def("__getstate__", &serialize<T> )
							.def("__setstate__", &setStateDeserialize<T> )
							.def("__str__", &prettyPrintString<T> )
							.def("__cmp__", &cppmlCmpPy<T> )
							.enable_pickling()
							;
			def(name.c_str(), (boost::python::object)T_.class_());

			return T_.class_();
			}

		static void parseErrorTranslator(SimpleParseError arg)
			{
			PyErr_SetString(PyExc_UserWarning, ("SimpleParseError: " + prettyPrintString(arg)).c_str());
			}

		static hash_type hashSimpleParseNode(const SimpleParseNode& node)
			{
			return node.hash();
			}

		static void exportPythonInterface()
			{
			using namespace boost::python;

			boost::python::register_exception_translator<SimpleParseError>(&parseErrorTranslator);

			defineSimpleCPPMLClass<SimpleParseNode>("SimpleParseNode")
				.def("parse", &parseStringToSimpleParse)
				.staticmethod("parse")
				.def("wrapString", &stringToStringConstant)
                .def("hash", &hashSimpleParseNode)
				.staticmethod("wrapString")
				;

			defineSimpleCPPMLClass<SimpleParseSeparator>("SimpleParseSeparator");
			defineSimpleCPPMLClass<SimpleParseGroup>("SimpleParseGroup");
			defineSimpleCPPMLClass<SimpleParseError>("SimpleParseError");
			defineSimpleCPPMLClass<SimpleParseRange>("SimpleParseRange");
			defineSimpleCPPMLClass<SimpleParsePosition>("SimpleParsePosition");

			PythonWrapper<ImmutableTreeVector<SimpleParseNode> >::exportPythonInterface("SimpleParseNode");
			}
};


#endif

