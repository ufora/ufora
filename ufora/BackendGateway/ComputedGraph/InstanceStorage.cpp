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
#include "InstanceStorage.hpp"
#include "LocationType.hpp"
#include "../../core/python/utilities.hpp"
#include "Graph.hpp"

using namespace Ufora::python;
using namespace boost::python;

namespace ComputedGraph {

/**********************
 *
 * InstanceStorage
 *
 * stores the python object wrappers around each Location and manages them. creates new node objects.
 * eventually will be responsible for hashing things.
 *
 ***********************/

InstanceStorage::InstanceStorage()
	{
	mIDTable = evalInModule("InstanceDataToIDLookupTable()", "ufora.BackendGateway.ComputedGraph.ComputedGraph");
	}

Location InstanceStorage::getObject(	PolymorphicSharedPtr<Graph> inGraph,
										PolymorphicSharedPtr<LocationType> inLocationType,
										dict inInstanceData,
										bool& needsInitialization
										)
	{
	dict instanceKeydata;

	for (map<id_type, object>::const_iterator it = inLocationType->mKeys.begin(); it != inLocationType->mKeys.end(); ++it)
		{
		id_type attrID = it->first;
		object attr = inGraph->idToStringObject(attrID);

		if (inInstanceData.has_key(attr))
			instanceKeydata[ attr ] = inInstanceData[ attr ];
			else
		if (inLocationType->mKeyDefaults[attrID] != object())
			instanceKeydata[ attr ] = inLocationType->mKeyDefaults[attrID](inInstanceData);
			else
			throw std::logic_error("construction of " + inLocationType->name() + " is missing key " + pyToString(attr));
		}

	id_type instanceID;
		{
		instanceID = boost::python::extract<id_type>(mIDTable(inLocationType->mClass, instanceKeydata));
		}

	needsInitialization = false;

	if (mInstances.find(instanceID) == mInstances.end())
		{
		needsInitialization = true;

		mInstances.insert(make_pair(instanceID, Location(inGraph, instanceID, inLocationType)));
		mPythonObjects[instanceID] = object(Location(inGraph, instanceID, inLocationType));

		for (map<id_type, object>::const_iterator it = inLocationType->mKeys.begin(); it != inLocationType->mKeys.end(); ++it)
			mInstanceData[make_pair(instanceID, it->first)] = instanceKeydata[ inGraph->idToStringObject(it->first) ];
		}

	return getObjectFromID(instanceID);
	}

object InstanceStorage::getObjectProperty(id_type inNodeID, id_type inPropertyID)
	{
	return mInstanceData[make_pair(inNodeID, inPropertyID)];
	}

Location InstanceStorage::getObjectFromID(id_type inNodeID)
	{
	lassert(mInstances.find(inNodeID) != mInstances.end());
	return mInstances.find(inNodeID)->second;
	}
object InstanceStorage::getPythonObject(id_type inNodeID)
	{
	return mPythonObjects[inNodeID];
	}

void InstanceStorage::remove(id_type inNodeID)
	{
	//TODO BUG brax: implement 'remove' in ComputedGraph
	}

size_t InstanceStorage::size(void) const
	{
	return mInstances.size();
	}


}
