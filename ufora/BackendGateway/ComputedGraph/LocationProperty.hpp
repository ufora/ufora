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
#pragma once

#include "Typedefs.hpp"
#include "Location.hpp"

namespace ComputedGraph {

class LocationProperty  {
public:
	LocationProperty(const LocationProperty& in) : m(in. m)
		{
		}

	LocationProperty(const Location& inLocation, id_type inPropID) : m(inLocation, inPropID)
		{
		}

	inline bool operator<(const LocationProperty& in) const
		{
		return m < in.m;
		}

	inline bool operator==(const LocationProperty& in) const
		{
		return m == in.m;
		}


	attr_type attributeType(void) const;

	boost::python::object getMutable(void) const;

	boost::python::object propertyDefinition(void) const;

	bool hasProperty(void) const;

	boost::python::object getClassAttribute(void) const;

	boost::python::object getFunction(void) const;

	boost::python::object getProperty(void) const;

	boost::python::object getUnknown(void) const;

	boost::python::object getKey(void) const;

	void setMutable(boost::python::object in) const;

	bool isLazy(void) const;

	std::string name(void) const;

	boost::python::object propertyNameObject(void) const;

	const Location& getLocation(void) const;

	id_type getPropertyID(void) const;

	std::pair<id_type, id_type> identifier(void) const;

private:
	std::pair<Location, id_type> m;
};


}
