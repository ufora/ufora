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


/**********************
 *
 * InstanceStorage
 *
 * stores the python object wrappers around each Location and manages them. creates new node objects.
 * eventually will be responsible for hashing things.
 *
 ***********************/

class InstanceStorage {
public:
	InstanceStorage();

	Location getObject(	PolymorphicSharedPtr<Graph> inGraph,
						PolymorphicSharedPtr<LocationType> inLocationType,
						boost::python::dict inInstanceData,
						bool& needsInitialization
						);

	boost::python::object getObjectProperty(id_type inNodeID, id_type inPropertyID);

	Location getObjectFromID(id_type inNodeID);

	boost::python::object getPythonObject(id_type inNodeID);

	void remove(id_type inNodeID);

	size_t size(void) const;

private:
	boost::python::object mIDTable;

	std::map<id_type, boost::python::object> mPythonObjects;

	std::map<id_type, Location>	mInstances;

	std::map<std::pair<id_type, id_type>, boost::python::object> mInstanceData;
};



}
