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
#include "../core/UnitTest.hpp"
#include "../core/threading/CallbackScheduler.hppml"
#include "CpuAssignmentDependencyGraph.hpp"
#include "QueueTestUtilities.hpp"

using namespace Cumulus;

namespace {

PolymorphicSharedPtr<CallbackScheduler> scheduler(CallbackScheduler::singletonForTesting());

PolymorphicSharedPtr<CpuAssignmentDependencyGraph> createGraph(void)
	{
	return PolymorphicSharedPtr<CpuAssignmentDependencyGraph>(
		new CpuAssignmentDependencyGraph(scheduler, PolymorphicSharedPtr<VectorDataManager>())
		);
	}

ComputationId compByIx(int ix)
	{
	return ComputationId::CreateIdForTesting(hash_type(ix));
	}

}


BOOST_AUTO_TEST_SUITE( test_Cumulus_CpuAssignmentDependencyGraph )

ComputationId computation1 = compByIx(1);

ComputationId computation2 = compByIx(2);

ComputationId computation3 = compByIx(3);

MachineId machine1(hash_type(1));

MachineId machine2(hash_type(2));

ComputationSystemwideCpuAssignment computation1NoAssignment =
	ComputationSystemwideCpuAssignment::withNoChildren( computation1, 0, 0);

ComputationSystemwideCpuAssignment computation1OneCpuDirect =
	ComputationSystemwideCpuAssignment::withNoChildren(computation1, 1, 0);

ComputationSystemwideCpuAssignment computation2NoAssignment =
	ComputationSystemwideCpuAssignment::withNoChildren(computation2, 0, 0);

ComputationSystemwideCpuAssignment computation2OneCpuDirect =
	ComputationSystemwideCpuAssignment::withNoChildren(computation2, 1, 0);

ComputationSystemwideCpuAssignment computation2OneCpuChild(
			computation2,
			emptyTreeMap() + computation1 + uint32_t(1),
			emptyTreeMap(),
			CheckpointStatus(),
			0,
			false,
			false,
			emptyTreeSet(),
			emptyTreeMap()
			);

ComputationSystemwideCpuAssignment computation3NoAssignment =
	ComputationSystemwideCpuAssignment::withNoChildren(computation3, 0, 0);

RootComputationComputeStatusChanged computation1Computing(
			machine1,
			computation1,
			1,
			0
			);

RootComputationComputeStatusChanged computation1NotComputing(
			machine1,
			computation1,
			0,
			0
			);


BOOST_AUTO_TEST_CASE( test_instantiate )
	{
	PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph = createGraph();
	}



BOOST_AUTO_TEST_CASE( test_simple_prioritize )
	{
	PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph = createGraph();

	graph->addMachine(machine1);

	auto queue = subscribeQueueToBroadcaster(
		graph->onCpuAssignmentChanged()
		);

	graph->markRootComputation(computation1);

	graph->updateDependencyGraph();

	BOOST_CHECK(true);
	assertQueueContainsAndRemove(*queue, computation1NoAssignment, scheduler);

	graph->handleRootComputationComputeStatusChanged(computation1Computing);

	graph->updateDependencyGraph();

	BOOST_CHECK(true);
	assertQueueContainsAndRemove(*queue,computation1OneCpuDirect, scheduler);

	graph->handleRootComputationComputeStatusChanged(computation1NotComputing);

	graph->updateDependencyGraph();

	BOOST_CHECK(true);
	assertQueueContainsAndRemove(*queue, computation1NoAssignment, scheduler);
	}

BOOST_AUTO_TEST_CASE( test_drop_machine_drops_active_cpus )
	{
	PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph = createGraph();

	graph->addMachine(machine1);

	graph->markRootComputation(computation1);
	graph->handleRootComputationComputeStatusChanged(computation1Computing);
	graph->updateDependencyGraph();

	auto queue = subscribeQueueToBroadcaster(
		graph->onCpuAssignmentChanged()
		);

	graph->dropMachine(machine1);

	assertQueueContainsAndRemove(*queue, computation1NoAssignment, scheduler);
	}

BOOST_AUTO_TEST_CASE( test_dependency_graph_flows_correctly )
	{
	PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph = createGraph();

	graph->addMachine(machine1);

	auto queue = subscribeQueueToBroadcaster(
		graph->onCpuAssignmentChanged()
		);


	graph->handleRootToRootDependencyCreated(RootToRootDependencyCreated(computation2, computation1));

	graph->markRootComputation(computation2);

	graph->updateDependencyGraph();

	BOOST_CHECK(true);

	scheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

	assertQueueContainsAndRemoveRegardlessOfOrder(*queue, computation2NoAssignment, scheduler);
	BOOST_CHECK(queue->size() == 0);

	graph->handleRootComputationComputeStatusChanged(
		RootComputationComputeStatusChanged(
			machine1,
			computation1,
			1,
			0
			)
		);

	graph->updateDependencyGraph();

	scheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();

	BOOST_CHECK(true);
	assertQueueContainsAndRemoveRegardlessOfOrder(*queue, computation2OneCpuChild, scheduler);
	BOOST_CHECK(queue->size() == 0);
	}

BOOST_AUTO_TEST_CASE( test_parent_cpu_counts )
	{
	PolymorphicSharedPtr<CpuAssignmentDependencyGraph> graph = createGraph();

	graph->addMachine(machine1);

	auto queue = subscribeQueueToBroadcaster(
		graph->onCpuAssignmentChanged()
		);

	map<ComputationId, ComputationSystemwideCpuAssignment> assignmentMap;

	auto drain = [&]() {
		scheduler->blockUntilPendingHaveExecutedAndImmediateQueueIsEmpty();
		while (auto val = queue->getNonblock())
			assignmentMap[val->computation()] = *val;
		};

	graph->handleRootToRootDependencyCreated(RootToRootDependencyCreated(compByIx(4), compByIx(3)));

	graph->handleRootToRootDependencyCreated(RootToRootDependencyCreated(compByIx(3), compByIx(2)));

	graph->handleRootToRootDependencyCreated(RootToRootDependencyCreated(compByIx(2), compByIx(1)));

	graph->markRootComputation(compByIx(4));

	graph->updateDependencyGraph();

	BOOST_CHECK(true);

	drain();
	BOOST_CHECK(assignmentMap.find(compByIx(4)) != assignmentMap.end());
	BOOST_CHECK(assignmentMap[compByIx(4)].cpusAssigned() == 0);

	graph->markRootComputation(compByIx(2));

	graph->updateDependencyGraph();

	BOOST_CHECK(true);

	drain();
	lassert(assignmentMap.find(compByIx(2)) != assignmentMap.end());
	BOOST_CHECK(assignmentMap[compByIx(2)].cpusAssigned() == 0);


	graph->handleRootComputationComputeStatusChanged(
		RootComputationComputeStatusChanged(
			machine1,
			compByIx(1),
			1,
			0
			)
		);

	graph->updateDependencyGraph();

	drain();

	BOOST_CHECK(true);

	BOOST_CHECK_EQUAL(assignmentMap[compByIx(4)].cpusAssigned(), 0);
	BOOST_CHECK_EQUAL(assignmentMap[compByIx(2)].cpusAssigned(), 1);
	}

BOOST_AUTO_TEST_SUITE_END()

