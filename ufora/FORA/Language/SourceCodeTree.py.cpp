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
#include "SourceCodeTree.hppml"

#include "../../core/python/ValueLikeCPPMLWrapper.hppml"
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../../core/containers/ImmutableTreeMap.py.hpp"

class SourceCodeTreeWrapper :
	public native::module::Exporter<SourceCodeTreeWrapper> {
public:
	std::string		 getModuleName(void)
		{
		return "FORA";
		}

	static Fora::SourceCodeTree constructModuleWithName(std::string name)
		{
		return Fora::SourceCodeTree::Module(name, null(), emptyTreeMap());
		}

	static Fora::SourceCodeTree constructModuleWithNameAndText(std::string name, std::string text)
		{
		return Fora::SourceCodeTree::Module(name, null() << text, emptyTreeMap());
		}

	static Fora::SourceCodeTree constructModuleWithNameAndChildren(std::string name, boost::python::list children)
		{
		ImmutableTreeMap<std::string, Fora::SourceCodeTree> childrenMap;

		for (long k = 0; k < boost::python::len(children); k++)
			{
			boost::python::extract<Fora::SourceCodeTree> extractor(children[k]);

			lassert_dump(extractor.check(), "Arguments to Fora::SourceCodeTree constructor must also be source code trees");

			Fora::SourceCodeTree child = extractor();

			childrenMap = childrenMap + child.name() + child;
			}

		return Fora::SourceCodeTree::Module(name, null(), childrenMap);
		}

	static Fora::SourceCodeTree constructModuleWithNameAndTextAndChildren(std::string name, std::string text, boost::python::list children)
		{
		ImmutableTreeMap<std::string, Fora::SourceCodeTree> childrenMap;

		for (long k = 0; k < boost::python::len(children); k++)
			{
			boost::python::extract<Fora::SourceCodeTree> extractor(children[k]);

			lassert_dump(extractor.check(), "Arguments to Fora::SourceCodeTree constructor must also be source code trees");

			Fora::SourceCodeTree child = extractor();

			childrenMap = childrenMap + child.name() + child;
			}

		return Fora::SourceCodeTree::Module(name, null() << text, childrenMap);
		}

	static Fora::SourceCodeTree constructScriptWithNameAndText(std::string name, std::string text)
		{
		return Fora::SourceCodeTree::Script(name, text);
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		boost::python::object cls;

		cls = ValueLikeCPPMLWrapper::exposeValueLikeCppmlType<Fora::SourceCodeTree>()
			.class_()
			.def("Module", constructModuleWithName)
			.def("Module", constructModuleWithNameAndText)
			.def("Module", constructModuleWithNameAndChildren)
			.def("Module", constructModuleWithNameAndTextAndChildren)
			.def("Script", constructScriptWithNameAndText)
			;

		def("SourceCodeTree", cls);

		PythonWrapper<ImmutableTreeMap<std::string, Fora::SourceCodeTree> >::exportPythonInterface("SourceCodeTree");
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<SourceCodeTreeWrapper>::mEnforceRegistration =
		native::module::ExportRegistrar<
			SourceCodeTreeWrapper>::registerWrapper();






