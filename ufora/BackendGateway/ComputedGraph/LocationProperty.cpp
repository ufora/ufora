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
#include "LocationProperty.hpp"
#include "LocationType.hpp"
#include "Graph.hpp"
#include "../../core/python/utilities.hpp"

using namespace Ufora::python;

namespace ComputedGraph {

attr_type LocationProperty::attributeType(void) const
	{
	return getLocation().attributeType(getPropertyID());
	}

boost::python::object LocationProperty::getMutable(void) const
	{
	return getLocation().getMutable(getPropertyID());
	}

boost::python::object LocationProperty::propertyDefinition(void) const
	{
	return getLocation().getPropertyDefinition(getPropertyID());
	}

bool LocationProperty::hasProperty(void) const
	{
	return getLocation().getGraph()->getPropertyStorage().has(*this);
	}

boost::python::object LocationProperty::getClassAttribute(void) const
	{
	return getLocation().getClassAttribute(getPropertyID());
	}

boost::python::object LocationProperty::getFunction(void) const
	{
	return getLocation().getFunction(getPropertyID());
	}

boost::python::object LocationProperty::getProperty(void) const
	{
	return getLocation().getGraph()->getPropertyStorage().getValue(*this);
	}

boost::python::object LocationProperty::getUnknown(void) const
	{
	return getLocation().getUnknown(getPropertyID());
	}

boost::python::object LocationProperty::getKey(void) const
	{
	return getLocation().getKey(getPropertyID());
	}

void LocationProperty::setMutable(boost::python::object in) const
	{
	getLocation().setMutable(getPropertyID(), in);
	}

bool LocationProperty::isLazy(void) const
	{
	return getLocation().getType()->isLazy(m.second);
	}

string LocationProperty::name(void) const
	{
	return getLocation().name() + ": " + pyToString(getLocation().getGraph()->idToStringObject(getPropertyID()));
	}

boost::python::object LocationProperty::propertyNameObject(void) const
	{
	return getLocation().getGraph()->idToStringObject(getPropertyID());
	}

const Location& LocationProperty::getLocation(void) const
	{
	return m.first;
	}

id_type LocationProperty::getPropertyID(void) const
	{
	return m.second;
	}

pair<id_type, id_type> LocationProperty::identifier(void) const
	{
	return make_pair(getLocation().getID(), m.second);
	}


}


