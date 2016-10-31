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

class LocationType : public PolymorphicSharedPtrBase<LocationType> {
private:
	LocationType(const LocationType& in) {}
	LocationType& operator=(const LocationType& in) { return *this; }
public:
	LocationType(Graph* inGraph, boost::python::object inClass);

	void update(Graph* inGraph, boost::python::object inClass);

	std::string name(void) const;

	attr_type getAttrType(const id_type& inID) const;

	boost::python::object getClass(void) const;

	class_id_type getClassID(void) const;

	bool	isLazy(const id_type& inID) const;

//private:
	std::map<id_type, boost::python::object> mFunctions;

	std::map<id_type, boost::python::object> mProperties;

	std::map<id_type, boost::python::object> mPropertySetters;

	std::map<id_type, bool> mIsLazyProperty;

	std::map<id_type, std::pair<boost::python::object, boost::python::object> > mMutables;	//default value and "onchanged"

	std::map<id_type, boost::python::object> mKeys;

	std::map<id_type, boost::python::object> mKeyDefaults;

	std::map<id_type, boost::python::object> mKeyValidators;

	std::map<id_type, boost::python::object> mClassAttributes;

	std::map<id_type, attr_type> mAttrTypes;

	boost::python::object  mInitializer;

	boost::python::object  mClass;

	boost::python::object  mDefersTo;
};




}



