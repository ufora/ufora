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
#include "JudgmentOnValueTree.hppml"

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"
#include "../python/FORAPythonUtil.hppml"

class JudgmentOnValueTreeWrapper :
	public native::module::Exporter<JudgmentOnValueTreeWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "FORA";
		}

	static JudgmentOnValueTree* treeFromList(boost::python::object inList)
		{
		//generic iterator...
		boost::python::object it = inList.attr("__iter__")();

		ImmutableTreeVector<pair<JudgmentOnValueTuple, uword_t> > jovts;

		try {
			while(1)
				{
				boost::python::object val = it.attr("next")();

				boost::python::extract<JudgmentOnValueTuple> e(val);

				if (!e.check())
					throw std::logic_error(
						"List arguments to JudgmentOnValueTree::__init__ must be JOVTs"
						);

				jovts = jovts + make_pair(e(), jovts.size());
				}
			}
		catch(...)
			{
			PyErr_Clear();
			}

		return new JudgmentOnValueTree(
			createJOVTreeRule(
				jovts,
				EqualFrequency()
				)
			);
		}

	static boost::python::object searchForJOVT(JudgmentOnValueTree& rule, JudgmentOnValueTuple& jovt)
		{
		Nullable<uword_t> tr = searchJOVTree(rule, jovt);

		if (tr)
			return boost::python::object(*tr);

		return boost::python::object();
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;
		
		class_<JudgmentOnValueTree>("JudgmentOnValueTree", no_init)
			.def("__init__", make_constructor(treeFromList))
			.def("__str__", prettyPrintString<JudgmentOnValueTree>)
			.def("searchForJOVT", searchForJOVT)
			;
		}
	
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<JudgmentOnValueTreeWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<
	JudgmentOnValueTreeWrapper>::registerWrapper();

