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
#include <stdint.h>
#include <boost/python.hpp>
#include "Location.hpp"
#include "LocationType.hpp"
#include "Graph.hpp"
#include "../../native/Registrar.hpp"
#include "../../core/python/CPPMLWrapper.hpp"
#include "../../core/python/ScopedPyThreads.hpp"

using namespace boost::python;
using namespace ComputedGraph;

class ComputedGraphLocationWrapper :
	public native::module::Exporter<ComputedGraphLocationWrapper> {
public:
	typedef ComputedGraph::Location location_type;

	typedef ComputedGraph::LocationProperty LocationProperty;

	typedef PolymorphicSharedPtr<ComputedGraph::Graph> graph_ptr;

	std::string		getModuleName(void)
		{
		return "ComputedGraph";
		}

	static object getattr(location_type& in, object attr)
		{
		ComputedGraph::LocationProperty p(in, Ufora::python::id(attr));

		if (p.attributeType() == ComputedGraph::attrUnknown)
			in.getGraph()->registerPropertyName(attr);

		return in.getGraph()->nodeAttribute(p);
		}

	static void setattr(location_type& in, object attr, object inVal)
		{
		in.getGraph()->setnodeProperty(in.getID(), attr, inVal);
		}

	static bool eq(location_type& in, object attr)
		{
		return Ufora::python::id(in.getPythonObject()) == Ufora::python::id(attr);
		}

	static int32_t hash(location_type& in)
		{
		return in.getID();
		}

	static object name(location_type& in)
		{
		Ufora::python::Holder h("intern('__str__')", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
		object s = h.get();

		if (in.attributeType(Ufora::python::id(s)) == ComputedGraph::attrFunction)
			return in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s)))();

		if (in.attributeType(Ufora::python::id(s)) != ComputedGraph::attrUnknown)
			return in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s)));

		return object(in.name());
		}

	static object add(location_type& in, object o)
		{
		static object s;

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__add__"));
			in.getGraph()->registerPropertyName(s);
			}

		return in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s)))(o);
		}

	static object type_(location_type& in)
		{
		return in.getType()->getClass();
		}

	static object mul(location_type& in, object o)
		{
		static object s;

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__mul__"));
			in.getGraph()->registerPropertyName(s);
			}

		return in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s)))(o);
		}

	static object rmul(location_type& in, object o)
		{
		static object s;

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__rmul__"));
			in.getGraph()->registerPropertyName(s);
			}

		return in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s)))(o);
		}

	static object dirty(location_type& in, object attr)
		{
		set<LocationProperty> downProps = in.getGraph()->getPropertyStorage().propertiesDirtying(LocationProperty(in, Ufora::python::id(attr)));

		py_list l;
		for (set<LocationProperty>::const_iterator it = downProps.begin(); it != downProps.end(); ++it)
			l.append(boost::python::make_tuple(it->getLocation().getPythonObject(), in.getGraph()->idToStringObject(it->getPropertyID())));

		return l;
		}

	static object downstream(location_type& in, object attr)
		{
		set<LocationProperty> downProps = in.getGraph()->getPropertyStorage().propertiesDowntree(LocationProperty(in, Ufora::python::id(attr)));

		py_list l;
		for (set<LocationProperty>::const_iterator it = downProps.begin(); it != downProps.end(); ++it)
			l.append(boost::python::make_tuple(it->getLocation().getPythonObject(), in.getGraph()->idToStringObject(it->getPropertyID())));

		return l;
		}

	static object upstream(location_type& in, object attr)
		{
		set<LocationProperty> downProps = in.getGraph()->getPropertyStorage().propertiesUptree(LocationProperty(in, Ufora::python::id(attr)));

		py_list l;
		for (set<LocationProperty>::const_iterator it = downProps.begin(); it != downProps.end(); ++it)
			l.append(boost::python::make_tuple(it->getLocation().getPythonObject(), in.getGraph()->idToStringObject(it->getPropertyID())));

		return l;
		}

	static boost::python::object reduce(location_type& in)
		{
		using namespace ComputedGraph;

		object classObj = in.getType()->getClass();
		dict keys;

		for (map<id_type, object>::const_iterator it = in.getType()->mKeys.begin(); it != in.getType()->mKeys.end(); ++it)
			keys[in.getGraph()->idToStringObject(it->first)] = in.getKey(it->first);

		return boost::python::make_tuple(classObj, boost::python::make_tuple(keys));
		}

	static boost::python::object call(boost::python::tuple inArgs, boost::python::dict inKW)
		{
		static object s;
		static object callFunc;

		location_type& in = boost::python::extract<location_type&>(inArgs[0]);

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__call__"));
			in.getGraph()->registerPropertyName(s);
			}

		if (callFunc == object())
			callFunc = Ufora::python::evalInModule("callFunc", "ufora.BackendGateway.ComputedGraph.ComputedGraph");

		object a(inArgs.slice(1,_));
		return callFunc(in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s))), a, inKW);
		}

	static boost::python::object setitem(boost::python::tuple inArgs, boost::python::dict inKW)
		{
		static object s;
		static object callFunc;

		location_type& in = boost::python::extract<location_type&>(inArgs[0]);

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__setitem__"));
			in.getGraph()->registerPropertyName(s);
			}

		if (callFunc == object())
			callFunc = Ufora::python::evalInModule("callFunc", "ufora.BackendGateway.ComputedGraph.ComputedGraph");

		object a(inArgs.slice(1,_));
		return callFunc(in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s))), a, inKW);
		}

	static boost::python::object getitem(boost::python::tuple inArgs, boost::python::dict inKW)
		{
		static object s;
		static object callFunc;

		location_type& in = boost::python::extract<location_type&>(inArgs[0]);

		if (s == object())
			{
			s = Ufora::python::evalInModule("intern", "ufora.BackendGateway.ComputedGraph.ComputedGraph")(string("__getitem__"));
			in.getGraph()->registerPropertyName(s);
			}

		if (callFunc == object())
			callFunc = Ufora::python::evalInModule("callFunc", "ufora.BackendGateway.ComputedGraph.ComputedGraph");

		object a(inArgs.slice(1,_));
		return callFunc(in.getGraph()->nodeAttribute(LocationProperty(in, Ufora::python::id(s))), a, inKW);
		}

	static PolymorphicSharedPtr<ComputedGraph::Graph> getgraph(location_type& in)
		{
		return PolymorphicSharedPtr<ComputedGraph::Graph>(in.getGraph());
		}

	void exportPythonWrapper()
		{
		using namespace boost::python;

		class_<location_type>("LocationRef_", no_init)
			.def("__getattr__", getattr)
			.def("__setattr__", setattr)
			.add_property("__graph__", getgraph)
			.def("__hash__", hash)
			.def("__eq__", eq)
			.def("__str__", name)
			.def("__repr__", name)
			.def("__down__", downstream)
			.def("__dirtying__", dirty)
			.def("__up__", upstream)
			.def("__add__", add)
			.def("__mul__", mul)
			.def("__rmul__", rmul)
			.def("__reduce__", reduce)
			.add_property("__location_class__", type_)
			.def("__call__", boost::python::raw_function(call, 1))
			.def("__getitem__", boost::python::raw_function(getitem, 1))
			.def("__setitem__", boost::python::raw_function(setitem, 1))
			;
		}
};






//explicitly instantiating the registration element causes the linker to need
//this file
template<>
char native::module::Exporter<ComputedGraphLocationWrapper>::mEnforceRegistration =
	native::module::ExportRegistrar<ComputedGraphLocationWrapper>::registerWrapper();




