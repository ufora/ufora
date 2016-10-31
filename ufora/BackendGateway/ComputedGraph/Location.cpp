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
#include "Location.hpp"
#include "LocationType.hpp"
#include "Graph.hpp"
#include "../../core/python/utilities.hpp"

using namespace Ufora::python;
using namespace boost::python;

namespace ComputedGraph {

boost::python::object Location::getPythonObject(void) const
	{
	return getGraph()->getInstanceStorage().getPythonObject(mObjectID);
	}
attr_type Location::attributeType(id_type inPropID) const
	{
	return getType()->getAttrType(inPropID);
	}
boost::python::object Location::getMutable(id_type inPropID) const
	{
	lassert(attributeType(inPropID) == attrMutable);
	return getGraph()->getPropertyStorage().getValue( LocationProperty(*this, inPropID) );
	}
void Location::setMutable(id_type inPropID, boost::python::object inO) const
	{
	lassert(attributeType(inPropID) == attrMutable);
	getGraph()->getPropertyStorage().setMutableProperty( LocationProperty(*this, inPropID), inO);
	}
boost::python::object Location::getKey(id_type inPropID) const
	{
	return getGraph()->getInstanceStorage().getObjectProperty(mObjectID, inPropID);
	}
bool Location::hasProperty(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrProperty);
	return getGraph()->getPropertyStorage().has( LocationProperty(*this, inProp) );
	}
boost::python::object Location::getProperty(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrProperty);
	return getGraph()->getPropertyStorage().getValue( LocationProperty(*this, inProp) );
	}
id_type Location::getID(void) const
	{
	return mObjectID;
	}
boost::python::object Location::getClassAttribute(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrClassAttribute);
	return getType()->mClassAttributes[inProp];
	}
boost::python::object Location::getUnknown(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrUnknown);
	if (getType()->mDefersTo != boost::python::object())
		{
		boost::python::object tr;

		tr = getType()->mDefersTo(getPythonObject());

		boost::python::extract<Location> e(tr);
		if (e.check())
			return getGraph()->nodeAttribute(LocationProperty(e, inProp));
			else
			return tr.attr(getGraph()->idToStringObject(inProp));
		}
		else
		throw std::logic_error("Location " + name() + " doesn't have property " + pyToString(getGraph()->idToStringObject(inProp)));
	}
boost::python::object Location::getFunction(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrFunction || attributeType(inProp) == attrNotCached);
	return getType()->mFunctions[inProp];
	}

boost::python::object Location::getPropertyDefinition(id_type inProp) const
	{
	lassert(attributeType(inProp) == attrProperty);
	return getType()->mProperties[inProp];
	}

std::string Location::name(void) const
	{
	return getType()->name() + "@" + boost::lexical_cast<std::string>(mObjectID);
	}

PolymorphicSharedPtr<Graph> Location::getGraph(void) const
	{
	return PolymorphicSharedPtr<Graph>(mGraphWeakPtr);
	}

PolymorphicSharedPtr<LocationType> Location::getType(void) const
	{
	return mTypePtr;
	}

}

