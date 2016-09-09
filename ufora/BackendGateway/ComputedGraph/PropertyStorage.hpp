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
#include "LocationProperty.hpp"
#include "../../core/containers/TwoWaySetMap.hpp"
#include "../../core/containers/MapWithIndex.hpp"

#include <set>

namespace ComputedGraph {

/**********************
 *
 * keeps track of the dependencies between properties.
 *
 * each node in here is either a mutable or a cached property, and is always represented by a LocationProperty
 *
 * we track:
 * 		dependencies between nodes (e.g. we say A->B if A needs B to be computed)
 *		"level" of the node, which is 1+ the max of the levels of the guys it depends on
 *		a list of orphaned nodes
 *		a list of root nodes (which are not orphaned)
 *		a list of dirty nodes (nonmutables which may need to be recomputed)
 *
 *
 *
 ***********************/

class PropertyStorage {
public:
		PropertyStorage(Graph* g);

		bool isRoot(LocationProperty inNode) const;

		void addRootNode(LocationProperty inNode, RootPtr inRootPtr);

		void dropRootNode(LocationProperty inNode, WeakRootPtr inRootPtr);

		bool isOrphaned(LocationProperty inNode) const;

		void markOrphaned(LocationProperty inNode);

		void markNotOrphaned(LocationProperty inNode);

		const std::set<LocationProperty>& getNonrootOrphans(void) const;

		const std::set<LocationProperty>& getNonrootNonmutableOrphans(void) const;

		const std::set<LocationProperty>& getOrphans(void) const;

		void setMutableProperty(LocationProperty inNode, const boost::python::object& inVal);

		void setProperty(
				LocationProperty inNode,
				const boost::python::object& inValue,
				const std::set< LocationProperty >& inNewDowntreeValues
				);

		unsigned long	scanRootsAndDrop(void);

		int32_t getLevel(LocationProperty inNode) const;

		bool isDirty(LocationProperty inNode) const;

		bool isClean(LocationProperty inNode) const;

		bool isLazy(LocationProperty inNode) const;

		void setLevel(LocationProperty inNode, int32_t inLevel);

		void setClean(LocationProperty inNode, bool inClean);

		void setLazy(LocationProperty inNode, bool inLazy);

		int32_t calcLevel(LocationProperty inNode) const;

		void getDirtyUptree(LocationProperty inNode, std::set<LocationProperty>& out);

		void getDirtyDowntree(LocationProperty inNode, std::set<LocationProperty>& out);

		bool computeLaziness(LocationProperty inNode);

		//returns whether the lazyness of the value changed
		bool recomputeLaziness(LocationProperty inNode);

		//returns whether the level goes up
		bool recomputeLevel(LocationProperty inNode);

		const std::set<LocationProperty>& propertiesDirtying(LocationProperty inProp) const;

		const std::set<LocationProperty>& propertiesDowntree(LocationProperty inProp) const;

		const std::set<LocationProperty>& propertiesUptree(LocationProperty inProp) const;

		void setDependencies(LocationProperty inNode, const std::set<LocationProperty>& inNewDowntreeValues);

		void deleteOrphan(LocationProperty inNode);

		bool has(LocationProperty inNode);

		boost::python::object getValue(LocationProperty inNode);

		bool hasDirty(bool inIncludeLazy) const;

		LocationProperty getLowestDirty(bool inIncludeLazy);

		void dirtyAllClassProperties(class_id_type classID);

		void dirtyAll(void);

		const std::map<LocationProperty, int32_t>& getMutables(void) const;
private:
		std::set<LocationProperty> mEmpty;

		std::map<LocationProperty, std::set<WeakRootPtr> > mNodeRoots;

		std::set<LocationProperty> mAllOrphanedProperties;

		std::set<LocationProperty> mNonrootOrphanedProperties;

		std::set<LocationProperty> mNonrootNonmutableOrphanedProperties;

		std::map<LocationProperty, int32_t> mMutablePropertyAccesses;

		Graph* mGraph;

		TwoWaySetMap<LocationProperty, LocationProperty> mDependencies;

		TwoWaySetMap<Location, id_type> mLocationProperties;

		TwoWaySetMap<class_id_type, LocationProperty> mClassPropertyLocations;

		std::map<LocationProperty, boost::python::object> mValues;

		std::map<LocationProperty, std::set<LocationProperty> > mDirtyingProperties;

		MapWithIndex<LocationProperty, std::pair<std::pair<bool, bool>, int32_t> > mNode_LazyCleanAndLevel;
};


}



