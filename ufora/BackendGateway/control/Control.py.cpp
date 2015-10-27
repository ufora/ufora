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
#include "Control.hppml"
#include "ControlInstance.hppml"
#include "ControlInstanceRoot.hppml"

using namespace boost::python;
using namespace std;

#include <stdint.h>
#include <boost/python.hpp>
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/lassert.hpp"
#include "../../core/python/ScopedPyThreads.hpp"

class ControlWrapper :
	public native::module::Exporter<ControlWrapper> {
public:
	std::string		getModuleName(void)
		{
		return "Control";
		}

	static Control New()
		{
		return Control::Empty();
		}

	static ControlInstancePtr createControlInstanceRoot(
					const Control& c, 
					PolymorphicSharedPtr<ComputedGraph::Graph>& inGraph, 
					boost::python::object inRoot
					)
		{
		ControlInstancePtr tr(
			new ControlInstance(c, 
				PolymorphicSharedPtr< ControlInstanceRoot>(
					new ControlInstanceRoot(inGraph, inRoot)
					)
				)
			);

		bool err = false;
		try {
			tr->initialize();
			}
		catch(std::exception& e)
			{
			cout << "error during initialization: " << e.what() << "\n";
			}
		catch(...)
			{
			tr->getRoot()->checkAnyErr();
			}

		return tr;
		}

	static Control layout(const LayoutRule& r, boost::python::list subcontrols)
		{
		vector<Control> v;
		for (int32_t k = 0; k < len(subcontrols); k++)
			v.push_back(extract<Control>(subcontrols[k]));
		return Control::Layout(r, LayoutGenerator::Fixed(v));
		}

	static Control layoutGenNoIdentifier(
					const LayoutRule& r, 
					boost::python::object keygen, 
					boost::python::object controlgen, 
					uword_t maxKeysToCache
					)
		{
		return layoutGen(r, keygen, controlgen, maxKeysToCache, "");
		}
	static Control layoutGen(
					const LayoutRule& r, 
					boost::python::object keygen, 
					boost::python::object controlgen, 
					uword_t maxKeysToCache,
					string identifier
					)
		{
		return Control::Layout(
			r, 
			LayoutGenerator::Variable(keygen, controlgen, maxKeysToCache, identifier)
			);
		}
	static Control getControl(ControlInstancePtr& self)
		{
		return self->getControl();
		}
	static boost::python::list getChildren(ControlInstancePtr& self)
		{
		return self->getChildren();
		}
	static ControlInstancePtr getParent(ControlInstancePtr& self)
		{
		return self->getParent();
		}
	static bool getIsInvalid(ControlInstancePtr& self)
		{
		return self->getIsInvalid();
		}
	static void pruneDirtyChildren(ControlInstancePtr& self)
		{
		return self->getRoot()->pruneDirtyChildren();
		}

	static void update(ControlInstancePtr& self)
		{
		self->getRoot()->update();
		}

	static std::string toString(ControlInstancePtr& self)
		{
		return self->toString();
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		class_<Control>("Control", no_init)
			.def("__str__", &prettyPrintString<Control>)
			;
		class_<LayoutRule>("LayoutRule", no_init);
		class_<ControlInstancePtr >("ControlInstance", no_init)
			.add_property("children", &getChildren)
			.add_property("control", &getControl)
			.add_property("parent", &getParent)
			.add_property("invalid", &getIsInvalid)
			.def("pruneDirtyChildren", &pruneDirtyChildren)
			.def("update", &update)
			.def("__str__", &toString)
			;

		def("Empty", &Control::Empty);
		def("Generated", &Control::Generated);
		def("Layout", &layout);
		def("Layout", &layoutGen);
		def("Layout", &layoutGenNoIdentifier);

		def("Stack", &LayoutRule::Stack);
		def("ArbitraryLayout", &LayoutRule::Anything);

		def("createCache", &createControlInstanceRoot);

		def("Control", &New);
		}
};

//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ControlWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<ControlWrapper>::registerWrapper();



