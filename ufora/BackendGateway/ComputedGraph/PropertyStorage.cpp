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
#include "Graph.hpp"
#include "Root.hpp"
#include "LocationType.hpp"
#include "PropertyStorage.hpp"
#include "../../core/Timers.hpp"
#include "../../core/Logging.hpp"
#include "../../core/python/utilities.hpp"

namespace ComputedGraph {

PropertyStorage::PropertyStorage(Graph* g) : mGraph(g)
	{
	}
bool PropertyStorage::isRoot(LocationProperty inNode) const
	{
	return mNodeRoots.find(inNode) != mNodeRoots.end();
	}
void PropertyStorage::addRootNode(LocationProperty inNode, RootPtr inRootPtr)
	{
	WeakRootPtr w(inRootPtr);
	mNodeRoots[inNode].insert(w);

	mNonrootOrphanedProperties.erase(inNode);
	mNonrootNonmutableOrphanedProperties.erase(inNode);
	}
void PropertyStorage::dropRootNode(LocationProperty inNode, WeakRootPtr inRootPtr)
	{
	mNodeRoots[inNode].erase(inRootPtr);
	if (mNodeRoots[inNode].size() == 0)
		{
		mNodeRoots.erase(inNode);

		if (isOrphaned(inNode))
			{
			mNonrootOrphanedProperties.insert(inNode);
			if (inNode.attributeType() != attrMutable)
				mNonrootNonmutableOrphanedProperties.insert(inNode);
			}
		}
	}
bool PropertyStorage::isOrphaned(LocationProperty inNode) const
	{
	return mAllOrphanedProperties.find(inNode) != mAllOrphanedProperties.end();
	}
void PropertyStorage::markOrphaned(LocationProperty inNode)
	{
	if (!isOrphaned(inNode))
		{
		mAllOrphanedProperties.insert(inNode);
		if (mNodeRoots.find(inNode) == mNodeRoots.end())
			{
			mNonrootOrphanedProperties.insert(inNode);
			if (inNode.attributeType() != attrMutable)
				mNonrootNonmutableOrphanedProperties.insert(inNode);
			}
		}
	}
void PropertyStorage::markNotOrphaned(LocationProperty inNode)
	{
	if (isOrphaned(inNode))
		{
		mAllOrphanedProperties.erase(inNode);
		mNonrootOrphanedProperties.erase(inNode);
		mNonrootNonmutableOrphanedProperties.erase(inNode);
		}
	}

const std::set<LocationProperty>& PropertyStorage::getNonrootOrphans(void) const
	{
	return mNonrootOrphanedProperties;
	}
const std::set<LocationProperty>& PropertyStorage::getNonrootNonmutableOrphans(void) const
	{
	return mNonrootNonmutableOrphanedProperties;
	}
const std::set<LocationProperty>& PropertyStorage::getOrphans(void) const
	{
	return mAllOrphanedProperties;
	}

void PropertyStorage::setMutableProperty(LocationProperty inNode, const boost::python::object& inVal)
	{
	lassert(inNode.attributeType() == attrMutable);

	setProperty(inNode, inVal, std::set< LocationProperty >());
	} 

void PropertyStorage::setProperty(
			LocationProperty inNode, 
			const boost::python::object& inValue, 
			const std::set< LocationProperty >& inNewDowntreeValues
			)
	{
	/****************
	 * to update a property we must do several things:
	 *
	 *		update the property value
	 * 		update the property list
	 * 		make sure we go through old dependencies and orphan any new orphans
	 * 		check that the value is different. if so, mark anybody "uptree" of this property as "dirty"
	 * 		update the level of the boost::python::object. We assume that the levels in the system are correct for
	 * 				- mutables (0)
	 * 				- clean nodes with everything clean below
	 * 			we have to be careful, in case a dirty property depends on another dirty property.
	 *
	 *******************/
	if (!mNode_LazyCleanAndLevel.hasKey(inNode))
		mNode_LazyCleanAndLevel.set(inNode, make_pair(make_pair(inNode.isLazy(), true), 0));

	bool valueChanged = true;
	bool valueExisted = mValues.find(inNode) != mValues.end();

	if (mValues.find(inNode) != mValues.end())
		{
		boost::python::object oldValue = mValues[inNode];

		if (mValues[inNode] == inValue)
			valueChanged = false;
		}
		else
		{
		//this property is new. by default it's orphaned.
		markOrphaned(inNode);
		mLocationProperties.insert(inNode.getLocation(), inNode.getPropertyID());
		mClassPropertyLocations.insert(inNode.getLocation().getType()->getClassID(), inNode);
		}

	mValues[inNode] = inValue;
	mDirtyingProperties.erase(inNode);

	setDependencies(inNode, inNewDowntreeValues);

	//std::set dirtiness
	setClean(inNode, true);
	recomputeLevel(inNode);
	recomputeLaziness(inNode);

	//now we have to std::set the cleanliness of our parents
	if (valueChanged)
		{
		//we mark all our uptrees as dirty
		const std::set<LocationProperty>& uptree(mDependencies.getKeys(inNode));

		for (std::set<LocationProperty>::const_iterator it = uptree.begin(); it != uptree.end(); ++it)
			{
			setClean(*it, false);
			mDirtyingProperties[*it].insert(inNode);
			}

		if (valueExisted && isRoot(inNode))
			{
			std::set<WeakRootPtr> toDrop;
			std::set<WeakRootPtr>::const_iterator end = mNodeRoots.find(inNode)->second.end();
			std::set<WeakRootPtr>::const_iterator it = mNodeRoots.find(inNode)->second.begin();

			for (;it != end; ++it)
				{
				RootPtr r = it->lock();
				if (!r)
					toDrop.insert(*it);
					else
					r->changed();
				}
			end = toDrop.end();
			it = toDrop.begin();
			for (;it != end; ++it)
				dropRootNode(inNode, *it);
			}
		}

	}

unsigned long	PropertyStorage::scanRootsAndDrop(void)
	{
	unsigned long ct = 0;
	std::set<std::pair<LocationProperty, WeakRootPtr> > toDrop;
	for (std::map<LocationProperty, std::set<WeakRootPtr> >::const_iterator it = mNodeRoots.begin(), it_end = mNodeRoots.end(); it != it_end; ++it)
		{
		std::set<WeakRootPtr>::const_iterator it2_end = it->second.end();
		std::set<WeakRootPtr>::const_iterator it2 = it->second.begin();

		for (;it2 != it2_end; ++it2)
			{
			RootPtr r = it2->lock();
			if (!r)
				toDrop.insert(make_pair(it->first, *it2));
			}
		}
	for (std::set<std::pair<LocationProperty, WeakRootPtr> >::iterator it = toDrop.begin(), it_end = toDrop.end(); it != it_end; ++it)
		dropRootNode(it->first, it->second);
	return toDrop.size();
	}

int32_t PropertyStorage::getLevel(LocationProperty inNode) const
	{
	return mNode_LazyCleanAndLevel.getValue(inNode).second;
	}

bool PropertyStorage::isDirty(LocationProperty inNode) const
	{
	return !mNode_LazyCleanAndLevel.getValue(inNode).first.second;
	}

bool PropertyStorage::isClean(LocationProperty inNode) const
	{
	return mNode_LazyCleanAndLevel.getValue(inNode).first.second;
	}

bool PropertyStorage::isLazy(LocationProperty inNode) const
	{
	return mNode_LazyCleanAndLevel.getValue(inNode).first.first;
	}

void PropertyStorage::setLevel(LocationProperty inNode, int32_t inLevel)
	{
	mNode_LazyCleanAndLevel.set(inNode, std::make_pair(mNode_LazyCleanAndLevel.getValue(inNode).first, inLevel));
	}

void PropertyStorage::setClean(LocationProperty inNode, bool inClean)
	{
	if (!mNode_LazyCleanAndLevel.hasKey(inNode))
		return;

	std::pair<std::pair<bool, bool>, int32_t> lazyCleanAndLevel = mNode_LazyCleanAndLevel.getValue(inNode);
	lazyCleanAndLevel.first.second = inClean;
	mNode_LazyCleanAndLevel.set(inNode, lazyCleanAndLevel);
	}

void PropertyStorage::setLazy(LocationProperty inNode, bool inLazy)
	{
	std::pair<std::pair<bool, bool>, int32_t> lazyCleanAndLevel = mNode_LazyCleanAndLevel.getValue(inNode);
	lazyCleanAndLevel.first.first = inLazy;
	mNode_LazyCleanAndLevel.set(inNode, lazyCleanAndLevel);
	}

int32_t PropertyStorage::calcLevel(LocationProperty inNode) const
	{
	int32_t myLevel = 0;
	const std::set<LocationProperty>& downtree(mDependencies.getValues(inNode));
	for (std::set<LocationProperty>::const_iterator it = downtree.begin(); it != downtree.end(); ++it)
		{
		lassert(mNode_LazyCleanAndLevel.hasKey(*it));
		
		int32_t l = getLevel(*it);
		if (myLevel < l+1)
			myLevel = l+1;
		}
	return myLevel;
	}
void PropertyStorage::getDirtyUptree(LocationProperty inNode, std::set<LocationProperty>& out)
	{
	const std::set<LocationProperty>& uptree(mDependencies.getKeys(inNode));
	for (std::set<LocationProperty>::const_iterator it = uptree.begin(); it != uptree.end(); ++it)
		if (isDirty(*it))
			out.insert(*it);
	}
void PropertyStorage::getDirtyDowntree(LocationProperty inNode, std::set<LocationProperty>& out)
	{
	const std::set<LocationProperty>& downtree(mDependencies.getValues(inNode));
	for (std::set<LocationProperty>::const_iterator it = downtree.begin(); it != downtree.end(); ++it)
		if (isDirty(*it))
			out.insert(*it);
	}
bool PropertyStorage::computeLaziness(LocationProperty inNode)
	{
	if (inNode.isLazy())
		return true;
	if (isRoot(inNode))
		return false;
	
	//we're not a lazy node, and not a root. So we're here because other nodes
	//depend on us. Check them. If all are lazy, we're lazy.
	//if none are lazy, we're not lazy (actually, we're orphaned)
	const std::set<LocationProperty>& uptree(mDependencies.getKeys(inNode));
	for (std::set<LocationProperty>::const_iterator it = uptree.begin(); it != uptree.end(); ++it)
		if (!isLazy(*it))
			return false;
	
	return uptree.size();
	}

//returns whether the lazyness of the value changed
bool PropertyStorage::recomputeLaziness(LocationProperty inNode)
	{
	bool curLaziness = isLazy(inNode);
	bool newLaziness = computeLaziness(inNode);
	setLazy(inNode, newLaziness);
	
	return curLaziness != newLaziness;
	}

//returns whether the level goes up
bool PropertyStorage::recomputeLevel(LocationProperty inNode)
	{
	int32_t l = getLevel(inNode);
	int32_t newL = calcLevel(inNode);
	setLevel(inNode, newL);
	return newL > l;
	}

const std::set<LocationProperty>& PropertyStorage::propertiesDirtying(LocationProperty inProp) const
	{
	if (mDirtyingProperties.find(inProp) == mDirtyingProperties.end())
		return mEmpty;

	return mDirtyingProperties.find(inProp)->second;
	}

const std::set<LocationProperty>& PropertyStorage::propertiesDowntree(LocationProperty inProp) const
	{
	return mDependencies.getValues(inProp);
	}

const std::set<LocationProperty>& PropertyStorage::propertiesUptree(LocationProperty inProp) const
	{
	return mDependencies.getKeys(inProp);
	}
void PropertyStorage::setDependencies(LocationProperty inNode, const std::set<LocationProperty>& inNewDowntreeValues)
	{
	std::set<LocationProperty> oldDowntree = mDependencies.getValues(inNode);

	//std::set the new downtree std::set
	mDependencies.update(inNode, inNewDowntreeValues);

	//update the orphan list
	for (std::set<LocationProperty>::iterator it = oldDowntree.begin(); it != oldDowntree.end(); ++it)
		{
		recomputeLaziness(*it);
		if (mDependencies.getKeys(*it).size() == 0)
			markOrphaned(*it);
		}
	for (std::set<LocationProperty>::iterator it = inNewDowntreeValues.begin(); it != inNewDowntreeValues.end(); ++it)
		{
		recomputeLaziness(*it);
		if (mDependencies.getKeys(*it).size() != 0)
			markNotOrphaned(*it);
		}
	}

void PropertyStorage::deleteOrphan(LocationProperty inNode)
	{
	lassert(isOrphaned(inNode));
	markNotOrphaned(inNode);

	setDependencies(inNode, std::set<LocationProperty>());

	mValues.erase(inNode);
	mNode_LazyCleanAndLevel.drop(inNode);

	mLocationProperties.drop(inNode.getLocation(), inNode.getPropertyID());
	mClassPropertyLocations.drop(inNode.getLocation().getType()->getClassID(), inNode);
	}
bool PropertyStorage::has(LocationProperty inNode)
	{
	return mValues.find(inNode) != mValues.end();
	}
boost::python::object PropertyStorage::getValue(LocationProperty inNode)
	{
	lassert_dump(has(inNode), inNode.name());

	if (inNode.attributeType() == attrMutable)
		mMutablePropertyAccesses[inNode] += 1;

	return mValues[inNode];
	}
bool PropertyStorage::hasDirty(bool inIncludeLazy) const
	{
	if (!mNode_LazyCleanAndLevel.keyCount())
		return false;

	std::pair<bool, bool> lazyAndClean = mNode_LazyCleanAndLevel.lowestValue().first;
	
	if (inIncludeLazy)
		{
		//if the lowest node is dirty, then it's dirty
		if (!lazyAndClean.second)
			return true;
		//if the lowest node is lazy and clean, then we're done
		if (lazyAndClean.first)
			return false;
		
		//the lowest node is not lazy, but it's clean. so we need to check the lowest nonlazy node
		
		//get the first node that's not less than <lazy, dirty>
		std::map<pair<std::pair<bool, bool>, int32_t>, std::set<LocationProperty> >::const_iterator it;
		it = mNode_LazyCleanAndLevel.getValueToKeys().lower_bound(std::make_pair(std::make_pair(true, false), 0));
		
		if (it == mNode_LazyCleanAndLevel.getValueToKeys().end())
			//all nodes are nonlazy
			return false;
		
		lassert(it->first.first.first); //it must be lazy
		return !it->first.first.second; //return whether it's dirty
		}
		else
		{
		//if the first node is lazy, there are no nonlazy nodes
		if (lazyAndClean.first)
			return false;
		
		return !lazyAndClean.second;
		}
	}
	
LocationProperty PropertyStorage::getLowestDirty(bool inIncludeLazy)
	{
	lassert(hasDirty(inIncludeLazy));
	
	std::map<std::pair<std::pair<bool, bool>, int32_t>, std::set<LocationProperty> >::const_iterator it;
	it = mNode_LazyCleanAndLevel.getValueToKeys().lower_bound(make_pair(make_pair(false, false), 0));
	
	if (!it->first.first.second)
		//it's dirty. MapWithIndex guarantees the std::set is not empty
		return *it->second.begin();
	
	//if we're here, we must be allowed to include lazy.
	//otherwise, there wouldn't be a dirty thing to return and we verified that at
	//the beginning of the function
	lassert(inIncludeLazy);
	it = mNode_LazyCleanAndLevel.getValueToKeys().lower_bound(make_pair(make_pair(true, false), 0));
	
	lassert(it != mNode_LazyCleanAndLevel.getValueToKeys().end());
	return *it->second.begin();
	}

void PropertyStorage::dirtyAllClassProperties(class_id_type classID)
	{
	const std::set<LocationProperty>& dirty(mClassPropertyLocations.getValues(classID));

	for (std::set<LocationProperty>::const_iterator it = dirty.begin();it != dirty.end(); ++it)
		if (it->attributeType() != attrMutable)
			setClean(*it, false);
	}
void PropertyStorage::dirtyAll(void)
	{
	std::set<LocationProperty> toDrop;
	for (std::map<LocationProperty, boost::python::object>::iterator it = mValues.begin(); it != mValues.end(); ++it)
		if (it->first.attributeType() != attrMutable)
			toDrop.insert(it->first);

	for (std::set<LocationProperty>::iterator it = toDrop.begin(); it != toDrop.end(); ++it)
		{
		mLocationProperties.drop(it->getLocation(), it->getPropertyID());
		mValues.erase(*it);
		mClassPropertyLocations.drop(it->getLocation().getType()->getClassID(), *it);
		mNode_LazyCleanAndLevel.drop(*it);
		}

	mDependencies = TwoWaySetMap<LocationProperty, LocationProperty>();
	mDirtyingProperties.clear();


	for (std::set<LocationProperty>::iterator it = toDrop.begin(); it != toDrop.end(); ++it)
		{
		if (mNodeRoots.find(*it) != mNodeRoots.end())
			{
			std::set<WeakRootPtr>::const_iterator end = mNodeRoots.find(*it)->second.end();
			std::set<WeakRootPtr>::const_iterator it2 = mNodeRoots.find(*it)->second.begin();

			for (;it2 != end; ++it2)
				{
				RootPtr r = it2->lock();
				if (r)
					r->changed();
				}
			}
		}
	}
const std::map<LocationProperty, int32_t>& PropertyStorage::getMutables(void) const
	{
	return mMutablePropertyAccesses;
	}


}
