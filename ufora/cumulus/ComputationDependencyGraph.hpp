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

#include "ComputationId.hppml"
#include "CumulusClientId.hppml"
#include "ComputationPriority.hppml"
#include "../core/containers/TwoWaySetMap.hpp"

namespace Cumulus {

class ComputationDependencyGraph {
public:
	ComputationDependencyGraph();

	void setCumulusClientPriority(
				const ComputationId& inId,
				const CumulusClientId& inClientId,
				const ComputationPriority& priority
				);

	void dropCumulusClient(
				const CumulusClientId& inClientId
				);

	void setDependencies(
				const ComputationId& inId,
				const std::set<ComputationId>& ids
				);

	//add a root-to-root dependency, and return whether it's considered new
	bool addRootToRootDependency(ComputationId source, ComputationId dest);

	bool isLocalComputation(const ComputationId& inId);

	void markComputationLocal(const ComputationId& inId);

	void markComputationNonlocal(const ComputationId& inId);

	void dropComputation(const ComputationId& inId);

	void update(std::set<ComputationId>& outLocalComputationsWithChangedPriorities,
				std::set<ComputationId>& outAllComputationsWithChangedPriorities
				);

	void update(std::set<ComputationId>& outLocalComputationsWithChangedPriorities);

	void update();

	ComputationPriority getPriority(const ComputationId& inId) const;

	ComputationPriority getLocalPriority(const ComputationId& inId) const;

	const std::map<pair<CumulusClientId, ComputationId>, ComputationPriority>&
														getClientPriorities() const;

	const std::map<ComputationId, ComputationPriority>& getAllPriorities() const;

	const std::set<ComputationId>&
	getComputationsDependingOn(const ComputationId& in) const;

	void getLocalComputationsDependingOn(
					const ComputationId& in,
					std::set<ComputationId>& outComputations
					) const;

	bool checkInternalState();

	const std::set<ComputationId>& getLocalComputations();

	const TwoWaySetMap<ComputationId, ComputationId>& getDependencies() const
		{
		return mDependencies;
		}

	const TwoWaySetMap<ComputationId, ComputationId>& getRootToRootDependencies() const
		{
		return mRootToRootDependencies;
		}

	const std::set<ComputationId>& orphanedLocalSplitComputations() const
		{
		return mOrphanedLocalSplitComputations;
		}

	void clientsRequesting(ComputationId id, std::set<CumulusClientId>& outClients) const;

	void clearOrphans()
		{
		mOrphanedLocalSplitComputations.clear();
		mOrphanedSplitComputations.clear();
		}

private:
	void ensureComputationInList_(const ComputationId& inId);

	ComputationPriority computePriorityFor(const ComputationId& inId);

    void updatePriority(
        const ComputationId& id,
        const ComputationPriority& newPriority,
        std::set<ComputationId>& outLocalComputationsWithChangedPriorities,
        std::set<ComputationId>& outAllComputationsWithChangedPriorities
        );

	TwoWaySetMap<ComputationId, ComputationId> mDependencies;

	std::set<ComputationId> mDirtyPriorities;

	std::set<ComputationId> mDirtySplitPriorities;

	std::set<ComputationId> mOrphanedLocalSplitComputations;

	std::set<ComputationId> mOrphanedSplitComputations;

	std::map<pair<CumulusClientId, ComputationId>, ComputationPriority> mClientPriorities;

	TwoWaySetMap<CumulusClientId, ComputationId> mClientIdToRootComputations;

	std::map<ComputationId, ComputationPriority> mAllPriorities;

	TwoWaySetMap<ComputationId, ComputationId> mRootToRootDependencies;

	TwoWaySetMap<ComputationId, ComputationId> mRootToSplitDependencies;

	std::set<ComputationId> mLocalComputations;
};

}

