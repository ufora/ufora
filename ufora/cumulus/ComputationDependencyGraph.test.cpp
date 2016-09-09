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
#include "../core/lassert.hpp"
#include "../core/UnitTest.hpp"

using namespace Cumulus;

namespace {

ComputationId idForInt(int i)
	{
	return ComputationId::CreateIdForTesting(hash_type(i));
	}

ComputationId idForInts(int i, int j)
	{
	return ComputationId::CreateIdForTesting(hash_type(i, j));
	}

ComputationPriority priorityForInt(uint64_t i)
	{
	return ComputationPriority(null() << i);
	}

CumulusClientId clientIdForInt(int i)
	{
	return CumulusClientId(hash_type(i));
	}

void setDeps(ComputationDependencyGraph& graph, ComputationId base)
	{
	std::set<ComputationId> deps;

	graph.setDependencies(base, deps);
	}

void setDeps(ComputationDependencyGraph& graph, ComputationId base, ComputationId dep1)
	{
	std::set<ComputationId> deps;

	deps.insert(dep1);

	graph.setDependencies(base, deps);

	if (base.isRoot() && dep1.isRoot())
		graph.addRootToRootDependency(base, dep1);
	}

void setDeps(	ComputationDependencyGraph& graph,
				ComputationId base,
				ComputationId dep1,
				ComputationId dep2
				)
	{
	std::set<ComputationId> deps;

	deps.insert(dep1);
	deps.insert(dep2);

	graph.setDependencies(base, deps);

	if (base.isRoot() && dep1.isRoot())
		graph.addRootToRootDependency(base, dep1);

	if (base.isRoot() && dep2.isRoot())
		graph.addRootToRootDependency(base, dep2);
	}

void update(ComputationDependencyGraph& graph)
	{
	std::set<ComputationId> updated;
	graph.update(updated);
	}

void assertPriorityRange(const ComputationDependencyGraph& graph, int low, int high, ComputationPriority level)
	{
	while (low < high)
		{
		lassert_dump(
			graph.getPriority(idForInt(low)).priorityLevel() == level.priorityLevel(),
			"priority for " << low << " is " << prettyPrintString(graph.getPriority(idForInt(low)))
				 << " not " << prettyPrintString(level)
			);
		low++;
		}
	}

void assertRangeIsCircular(const ComputationDependencyGraph& graph, int low, int high)
	{
	while (low < high)
		{
		lassert_dump(
			graph.getPriority(idForInt(low)).isCircular(),
			"priority for " << low << " is not circular. Got: "
			<< prettyPrintString(graph.getPriority(idForInt(low)))
			);
		low++;
		}
	}

}
BOOST_AUTO_TEST_SUITE( test_ComputationDependencyGraph )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	ComputationDependencyGraph graph;

	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(1));
	update(graph);

	assertPriorityRange(graph, 0, 1, priorityForInt(1));
	}

BOOST_AUTO_TEST_CASE( test_dependencies )
	{
	ComputationDependencyGraph graph;

	setDeps(graph, idForInt(0), idForInt(1));
	setDeps(graph, idForInt(1), idForInt(2));

	update(graph);

	//priorities are all null
	assertPriorityRange(graph, 0, 3, ComputationPriority());

	//set a priority and verify the state
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(1));

	//states are not updated yet
	assertPriorityRange(graph, 0, 3, ComputationPriority());

	update(graph);

	//states should be updated by now
	assertPriorityRange(graph, 0, 3, priorityForInt(1));

	//turn the external priority off
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), ComputationPriority());
	update(graph);

	assertPriorityRange(graph, 0, 3, ComputationPriority());

	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(1));
	update(graph);

	//drop the middle computation in the chain
	graph.dropComputation(idForInt(1));

	update(graph);

	BOOST_CHECK(graph.getPriority(idForInt(0)) == ComputationPriority(1, 1));
	BOOST_CHECK(graph.getPriority(idForInt(1)).isNull());
	BOOST_CHECK(graph.getPriority(idForInt(2)).isNull());

	graph.dropComputation(idForInt(0));
	graph.dropComputation(idForInt(2));

	BOOST_CHECK(graph.getClientPriorities().size() != 0);
	BOOST_CHECK(graph.getAllPriorities().size() == 0);

	graph.dropCumulusClient(clientIdForInt(0));
	BOOST_CHECK(graph.getClientPriorities().size() == 0);
	}

BOOST_AUTO_TEST_CASE( test_external_clients )
	{
	ComputationDependencyGraph graph;

	setDeps(graph, idForInt(0), idForInt(1));
	setDeps(graph, idForInt(1), idForInt(2));

	BOOST_CHECK(true);

	//set a priority and verify the state
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(1));
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(1));

	BOOST_CHECK(true);

	//set a second priority
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(1), priorityForInt(2));
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(2));

	BOOST_CHECK(true);

	//set the first priority up a second time
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(3));
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(3));

	BOOST_CHECK(true);

	//set the first priority to null
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), ComputationPriority());
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(2));

	BOOST_CHECK(true);

	//put it back
	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(2));
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(2));

	BOOST_CHECK(true);

	//drop the entire client
	graph.dropCumulusClient(clientIdForInt(0));
	update(graph);
	assertPriorityRange(graph, 0, 3, priorityForInt(2));

	BOOST_CHECK(true);

	//drop the other client
	graph.dropCumulusClient(clientIdForInt(1));
	update(graph);
	assertPriorityRange(graph, 0, 3, ComputationPriority());
	}

BOOST_AUTO_TEST_CASE( test_local )
	{
	ComputationDependencyGraph graph;

	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(1));
	setDeps(graph, idForInt(0), idForInt(1));
	setDeps(graph, idForInt(1), idForInt(2));

	graph.markComputationLocal(idForInt(1));

		{
		std::set<ComputationId> updated;
		graph.update(updated);

		//because we marked the computation 'local' we should be able to see it here
		BOOST_CHECK(updated.size() == 1);
		BOOST_CHECK(updated.find(idForInt(1)) != updated.end());

		assertPriorityRange(graph, 0, 3, priorityForInt(1));
		}

	graph.markComputationNonlocal(idForInt(1));

	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priorityForInt(2));

		{
		std::set<ComputationId> updated;
		graph.update(updated);

		//because we marked the computation 'nonlocal' the set should be empty
		BOOST_CHECK(updated.size() == 0);

		assertPriorityRange(graph, 0, 3, priorityForInt(2));
		}
	}

BOOST_AUTO_TEST_CASE( circular_dependencies_1 )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	graph.setCumulusClientPriority(idForInt(0), clientIdForInt(0), priority);
	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);
	update(graph);

	setDeps(graph, idForInt(0), idForInt(1));
	setDeps(graph, idForInt(1), idForInt(0));

	update(graph);

	BOOST_CHECK(true);

	assertPriorityRange(graph, 0, 2, priority.makeCircular());

	BOOST_CHECK(true);

	assertRangeIsCircular(graph, 0, 2);
	}

BOOST_AUTO_TEST_CASE( circular_dependencies_2 )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	setDeps(graph, idForInt(1), idForInt(2));
	setDeps(graph, idForInt(3), idForInt(4));
	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);
	graph.setCumulusClientPriority(idForInt(3), clientIdForInt(0), priority);

	update(graph);

	setDeps(graph, idForInt(4), idForInt(1));
	setDeps(graph, idForInt(2), idForInt(3));

	update(graph);

	BOOST_CHECK(true);

	assertPriorityRange(graph, 1, 5, priority.makeCircular());

	BOOST_CHECK(true);

	assertRangeIsCircular(graph, 1, 5);
	}

BOOST_AUTO_TEST_CASE( circular_dependencies_3 )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	setDeps(graph, idForInt(1), idForInt(2));
	setDeps(graph, idForInt(2), idForInt(3));
	setDeps(graph, idForInt(3), idForInt(4), idForInt(5));
	setDeps(graph, idForInt(5), idForInt(6));
	setDeps(graph, idForInt(6), idForInt(7));
	setDeps(graph, idForInt(7), idForInt(8));
	setDeps(graph, idForInt(8), idForInt(9));

	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);

	update(graph);

	assertPriorityRange(graph, 1, 10, priority);

	BOOST_CHECK(true);

	setDeps(graph, idForInt(9), idForInt(5));
	setDeps(graph, idForInt(4), idForInt(1));

	update(graph);

	assertRangeIsCircular(graph, 1, 10);
	}

BOOST_AUTO_TEST_CASE( circular_dependencies_4 )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	setDeps(graph, idForInt(1), idForInt(1));

	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);

	update(graph);

	BOOST_CHECK(true);

	assertPriorityRange(graph, 1, 2, priority);

	BOOST_CHECK(true);

	assertRangeIsCircular(graph, 1, 2);
	}

BOOST_AUTO_TEST_CASE( trees_1 )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	setDeps(graph, idForInt(1), idForInt(2));
	setDeps(graph, idForInt(2), idForInt(3), idForInt(4));

	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);

	update(graph);

	BOOST_CHECK(true);

	assertPriorityRange(graph, 1, 5, priority);

	BOOST_CHECK(true);
	}

BOOST_AUTO_TEST_CASE( single_node )
	{
	ComputationDependencyGraph graph;

	auto priority = priorityForInt(1);

	graph.setCumulusClientPriority(idForInt(1), clientIdForInt(0), priority);

	update(graph);

	BOOST_CHECK(true);

	assertPriorityRange(graph, 1, 2, priority);
	}

BOOST_AUTO_TEST_SUITE_END( )

