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

#include "ComputationStatusOnMachineChanged.hppml"
#include "RootComputationComputeStatusChanged.hppml"
#include "ComputationSystemwideCpuAssignment.hppml"
#include "RootToRootDependencyCreated.hppml"
#include "CheckpointStatusUpdateMessage.hppml"

#include "../core/EventBroadcaster.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "ComputationIsCurrentlyCheckpointing.hppml"

namespace Cumulus {

/************************

CpuAssignmentDependencyGraph

Responsible for tracking the state of computations in the system,
and determining how many CPUs are assigned to root computations.


*************************/

class CpuAssignmentDependencyGraphImpl;

class CpuAssignmentDependencyGraph : 
			public PolymorphicSharedPtrBase<CpuAssignmentDependencyGraph> {
public:
	CpuAssignmentDependencyGraph(
				PolymorphicSharedPtr<CallbackScheduler> inCallbackScheduler,
				PolymorphicSharedPtr<VectorDataManager> inVDM
				);

	void addMachine(MachineId inMachine);

	void dropMachine(MachineId inMachine);

	void handleRootToRootDependencyCreated(RootToRootDependencyCreated message);

	void handleRootComputationComputeStatusChanged(RootComputationComputeStatusChanged change);

	uint64_t computeBytecountForHashes(ImmutableTreeSet<hash_type> hashes);

	void handleCheckpointStatusUpdateMessage(CheckpointStatusUpdateMessage msg);

	void handleComputationIsCurrentlyCheckpointing(ComputationIsCurrentlyCheckpointing status);

	//indicate that we want to receive updates about a particular computation
	void markRootComputation(const ComputationId& computation);

	void markNonrootComputation(const ComputationId& computation);

	EventBroadcaster<ComputationSystemwideCpuAssignment>& onCpuAssignmentChanged();

	void updateDependencyGraph();

private:
	PolymorphicSharedPtr<CpuAssignmentDependencyGraphImpl> mImpl;
};

}


