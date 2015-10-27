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
#include "ComputationDependencyGraph.hpp"
#include "../core/cppml/CPPMLPrettyPrinter.hppml"
#include "../core/Logging.hpp"

#include <stack>

namespace Cumulus {

ComputationDependencyGraph::ComputationDependencyGraph()
	{

	}

void ComputationDependencyGraph::ensureComputationInList_(const ComputationId& inId)
	{
	if (inId.isRoot())
		return;

	if (!mRootToSplitDependencies.hasValue(inId))
		{
		mRootToSplitDependencies.insert(inId.rootComputation(), inId);
		mDirtySplitPriorities.insert(inId);
		}
	}
	
void ComputationDependencyGraph::setCumulusClientPriority(
				const ComputationId& inId, 
				const CumulusClientId& inClientId,
				const ComputationPriority& priority
				)
	{
	lassert(inId.isRoot());

	if (priority.isNull())
		{
		mClientIdToRootComputations.drop(inClientId, inId);
		mClientPriorities.erase(make_pair(inClientId, inId));
		}
	else
		{
		mClientIdToRootComputations.insert(inClientId, inId);
		mClientPriorities[make_pair(inClientId, inId)] = priority;
		}

	mDirtyPriorities.insert(inId);
	}

bool ComputationDependencyGraph::addRootToRootDependency(ComputationId source, ComputationId dest)
	{
	lassert(source.isRoot());
	lassert(dest.isRoot());

	if (mRootToRootDependencies.contains(source,dest))
		return false;

	mRootToRootDependencies.insert(source, dest);
	mDirtyPriorities.insert(dest);
	return true;
	}

void ComputationDependencyGraph::dropCumulusClient(
				const CumulusClientId& inClientId
				)
	{
	const std::set<ComputationId>& current = 
										mClientIdToRootComputations.getValues(inClientId);

	for (auto it = current.begin(); it != current.end(); ++it)
		{
		mDirtyPriorities.insert(*it);
		mClientPriorities.erase(make_pair(inClientId, *it));
		}

	mClientIdToRootComputations.dropKey(inClientId);
	}

void ComputationDependencyGraph::setDependencies(
			const ComputationId& inId, 
			const std::set<ComputationId>& ids
			)
	{
	ensureComputationInList_(inId);

	const std::set<ComputationId>& current = mDependencies.getValues(inId);

	if (current == ids)
		return;

	for (auto id: current)
		if (!id.isRoot() && ids.find(id) == ids.end() && 
				mDependencies.getKeys(id).size() == 1)
		{
		mOrphanedSplitComputations.insert(id);

		if (mLocalComputations.find(id) != mLocalComputations.end())
			mOrphanedLocalSplitComputations.insert(id);
		}

	for (auto id: ids)
		ensureComputationInList_(id);

	for (auto id: ids)
		{
		mOrphanedLocalSplitComputations.erase(id);
		mOrphanedSplitComputations.erase(id);
		}

	mDependencies.update(inId, ids);
	}

bool ComputationDependencyGraph::isLocalComputation(const ComputationId& inId)
	{
	return mLocalComputations.find(inId) != mLocalComputations.end();
	}

void ComputationDependencyGraph::markComputationLocal(const ComputationId& inId)
	{
	mLocalComputations.insert(inId);
	ensureComputationInList_(inId);

	if (!inId.isRoot() && mOrphanedSplitComputations.find(inId) != mOrphanedSplitComputations.end())
		mOrphanedLocalSplitComputations.insert(inId);
	}

void ComputationDependencyGraph::markComputationNonlocal(const ComputationId& inId)
	{
	mOrphanedLocalSplitComputations.erase(inId);
	mLocalComputations.erase(inId);
	}

void ComputationDependencyGraph::dropComputation(const ComputationId& inId)
	{
	if (inId.isRoot())
		{
		for (auto child: mRootToRootDependencies.getValues(inId))
			mDirtyPriorities.insert(child);
	
		for (auto child: mRootToSplitDependencies.getValues(inId))
			mDirtySplitPriorities.insert(child);
		}

	mAllPriorities.erase(inId);
	mLocalComputations.erase(inId);
	mDependencies.dropValue(inId);
	mDependencies.dropKey(inId);
	mRootToSplitDependencies.dropValue(inId);
	mRootToSplitDependencies.dropKey(inId);
	mDirtySplitPriorities.erase(inId);
	mOrphanedLocalSplitComputations.erase(inId);
	mOrphanedSplitComputations.erase(inId);

	mRootToRootDependencies.dropValue(inId);
	mRootToRootDependencies.dropKey(inId);
	}

void ComputationDependencyGraph::update(
			std::set<ComputationId>& outLocalComputationsWithChangedPriorities,
			std::set<ComputationId>& outAllComputationsWithChangedPriorities
			)
	{
	outLocalComputationsWithChangedPriorities.clear();
	outAllComputationsWithChangedPriorities.clear();

	long passesWhereSetIsStable = 0;

	while (mDirtyPriorities.size())
		{
		std::set<ComputationId> newDirty;

		std::set<ComputationId> toCheck = mDirtyPriorities;

		while(toCheck.size())
			{
			ComputationId id = *toCheck.begin();
			toCheck.erase(id);
			lassert(id.isRoot());

			ComputationPriority newPriority = computePriorityFor(id);

			if (newPriority != mAllPriorities[id])
				{
				mAllPriorities[id] = newPriority;

				const std::set<ComputationId>& children = mRootToRootDependencies.getValues(id);
	
				newDirty.insert(id);

				for (auto it = children.begin(); it != children.end(); ++it)
					{
					if (newDirty.find(*it) == newDirty.end())
						{
						newDirty.insert(*it);
						toCheck.insert(*it);
						}
					}

				outAllComputationsWithChangedPriorities.insert(id);

				if (mLocalComputations.find(id) != mLocalComputations.end())
					outLocalComputationsWithChangedPriorities.insert(id);
				}
			}

		if (mDirtyPriorities != newDirty)
			{
			mDirtyPriorities = newDirty;
			passesWhereSetIsStable = 0;
			}
		else 
			{
			passesWhereSetIsStable++;
			
			if (passesWhereSetIsStable > 1)
				{
				// this subset is circular
				for (auto id: mDirtyPriorities)
					updatePriority(
						id,
						mAllPriorities[id].makeCircular(),
						outLocalComputationsWithChangedPriorities,
						outAllComputationsWithChangedPriorities
						);

				mDirtyPriorities.clear();
				}
			}
		}

	std::set<ComputationId> toCheck = outAllComputationsWithChangedPriorities;

	//then check that all splits are correctly accounted for
	for (auto rootId: toCheck)
		for (auto split: mRootToSplitDependencies.getValues(rootId))
			mDirtySplitPriorities.insert(split);

	for (auto split: mDirtySplitPriorities)
		{
		ComputationPriority newPri = computePriorityFor(split);

		if (mAllPriorities[split] != newPri)
			{
			mAllPriorities[split] = newPri;
			outAllComputationsWithChangedPriorities.insert(split);
			if (mLocalComputations.find(split) != mLocalComputations.end())
				outLocalComputationsWithChangedPriorities.insert(split);
			}
		}

	mDirtySplitPriorities.clear();
	}

inline void ComputationDependencyGraph::updatePriority( 
			const ComputationId& id, 
			const ComputationPriority& newPriority,
			std::set<ComputationId>& outLocalComputationsWithChangedPriorities,
			std::set<ComputationId>& outAllComputationsWithChangedPriorities
			)
	{
	mAllPriorities[id] = newPriority;

	outAllComputationsWithChangedPriorities.insert(id);

	if (mLocalComputations.find(id) != mLocalComputations.end())
		outLocalComputationsWithChangedPriorities.insert(id);
	}

void ComputationDependencyGraph::update(
			std::set<ComputationId>& outLocalComputationsWithChangedPriorities
			)
	{
	std::set<ComputationId> throwAway;
	
	update(outLocalComputationsWithChangedPriorities, throwAway);
	}

void ComputationDependencyGraph::update()
	{
	std::set<ComputationId> throwAway;
	std::set<ComputationId> throwAway2;

	update(throwAway, throwAway2);
	}

ComputationPriority ComputationDependencyGraph::computePriorityFor(const ComputationId& inId)
	{
	if (inId.isSplit())
		return computePriorityFor(inId.rootComputation())
					.priorityForSplitComputation(inId.getSplit().treeDepth());

	ComputationPriority priority;

	const std::set<CumulusClientId>& clients = mClientIdToRootComputations.getKeys(inId);

	for (auto it = clients.begin(); it != clients.end(); ++it)
		{
		ComputationPriority clientPriority = 
			mClientPriorities[make_pair(*it, inId)].priorityForDependentComputation();
		
		if (priority.isShallower(clientPriority))
			priority = clientPriority;
		}

	const std::set<ComputationId>& parents = mRootToRootDependencies.getKeys(inId);

	for (auto it = parents.begin(); it != parents.end(); ++it)
		{
		ComputationPriority parentPriority = getPriority(*it).priorityForDependentComputation();

		if (priority.isShallower(parentPriority))
			priority = parentPriority;
		}

	return priority;
	}

ComputationPriority ComputationDependencyGraph::getPriority(const ComputationId& inId) const
	{
	auto it = mAllPriorities.find(inId);

	if (it != mAllPriorities.end())
		return it->second;

	return ComputationPriority();
	}

const std::map<pair<CumulusClientId, ComputationId>, ComputationPriority>& 
ComputationDependencyGraph::getClientPriorities() const
	{
	return mClientPriorities;
	}

const std::map<ComputationId, ComputationPriority>& 
ComputationDependencyGraph::getAllPriorities() const
	{
	return mAllPriorities;
	}

const std::set<ComputationId>& 
ComputationDependencyGraph::getComputationsDependingOn(const ComputationId& in) const
	{
	return mDependencies.getKeys(in);
	}

void ComputationDependencyGraph::getLocalComputationsDependingOn(
				const ComputationId& in, 
				std::set<ComputationId>& outComputations
				) const
	{
	const std::set<ComputationId>& computations = getComputationsDependingOn(in);

	for (auto it = computations.begin(); it != computations.end(); ++it)
		if (mLocalComputations.find(*it) != mLocalComputations.end())
			outComputations.insert(*it);
	}

ComputationPriority ComputationDependencyGraph::getLocalPriority(
				const ComputationId& in
				) const
	{
	if (mLocalComputations.find(in) == mLocalComputations.end())
		return ComputationPriority();

	return getPriority(in);
	}

bool ComputationDependencyGraph::checkInternalState()
	{
	bool isValid = true;

	lassert(!mDirtyPriorities.size());

	for (auto it = mAllPriorities.begin(); it != mAllPriorities.end(); ++it)
		if (it->second != computePriorityFor(it->first))
			{
			LOG_WARN << "ComputationDependencyGraph had " << prettyPrintString(it->second)
				<< " as priority for " << prettyPrintString(it->first) << " instead of "
				<< prettyPrintString(computePriorityFor(it->first));
			isValid = false;
			}

	for (auto it = mRootToRootDependencies.getKeysToValues().begin(); 
									it != mRootToRootDependencies.getKeysToValues().end();++it)
		if (mAllPriorities.find(it->first) == mAllPriorities.end() && 
				!computePriorityFor(it->first).isNull())
			{
			LOG_WARN 
				<< "ComputationDependencyGraph had dependencies for "
				<< prettyPrintString(it->first) << " but no priority."
				;
			isValid = false;
			}

	return isValid;
	}

const std::set<ComputationId>& ComputationDependencyGraph::getLocalComputations()
	{
	return mLocalComputations;
	}

}

