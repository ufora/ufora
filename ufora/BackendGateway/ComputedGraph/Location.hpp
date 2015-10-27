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

namespace ComputedGraph {

class Location {
public:
	Location(const Location& in)
		{
		mGraphWeakPtr = in.mGraphWeakPtr;
		mObjectID = in.mObjectID;
		mTypePtr = in.mTypePtr;
		}

	Location(	const PolymorphicSharedPtr<Graph>& inGraph, id_type inObjectID, const PolymorphicSharedPtr<LocationType>& inType)
		{
		mGraphWeakPtr = inGraph;
		mObjectID = inObjectID;
		mTypePtr = inType;
		}

	inline Location& operator=(const Location& in)
		{
		mGraphWeakPtr = in.mGraphWeakPtr;
		mObjectID = in.mObjectID;
		mTypePtr = in.mTypePtr;

		return *this;
		}

	inline bool operator==(const Location& in) const
		{
		return mObjectID == in.mObjectID;
		}
	inline bool operator<(const Location& in) const
		{
		return mObjectID < in.mObjectID;
		}

	boost::python::object getPythonObject(void) const;

	attr_type attributeType(id_type inPropID) const;

	boost::python::object getMutable(id_type inPropID) const;

	void setMutable(id_type inPropID, boost::python::object inO) const;
	
	boost::python::object getKey(id_type inPropID) const;
	
	bool hasProperty(id_type inProp) const;
	
	boost::python::object getProperty(id_type inProp) const;
	
	id_type getID(void) const;
	
	boost::python::object getClassAttribute(id_type inProp) const;
	
	boost::python::object getUnknown(id_type inProp) const;
	
	boost::python::object getFunction(id_type inProp) const;

	boost::python::object getPropertyDefinition(id_type inProp) const;
	
	std::string name(void) const;

	PolymorphicSharedPtr<Graph> getGraph(void) const;
	
	PolymorphicSharedPtr<LocationType> getType(void) const;
	
private:
	PolymorphicSharedPtr<LocationType> mTypePtr;
	
	PolymorphicSharedPtr<Graph> mGraphWeakPtr;

	id_type mObjectID;
};


}


