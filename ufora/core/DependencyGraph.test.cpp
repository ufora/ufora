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
#include "DependencyGraph.hpp"
#include "UnitTest.hpp"
#include "Logging.hpp"
#include "cppml/CPPMLPrettyPrinter.hppml"

using namespace DependencyGraph;

namespace {

int addOne(boost::shared_ptr<Mutable<int> > in)
	{
	return in->get() + 1;
	}

float brownian(
			boost::shared_ptr<ComputedProperty<float> > left, 
			boost::shared_ptr<ComputedProperty<float> > right
			)
	{
	float avg = (left->get() + right->get())/2;

	return std::max<float>(avg, 0.0);
	}

}

BOOST_AUTO_TEST_SUITE( test_DependencyGraph )

BOOST_AUTO_TEST_CASE( test_basic )
	{
	Graph graph;

	boost::shared_ptr<Mutable<int> > aMutable(new Mutable<int>());

	boost::function0<int> f = boost::bind(&addOne, aMutable);

	boost::shared_ptr<ComputedProperty<int> > aProperty(bind(graph, f));

	aMutable->set(10);
	BOOST_CHECK_EQUAL(aMutable->get(), 10);

	aProperty->get();

	graph.recompute();

	BOOST_CHECK_EQUAL(aProperty->get(), 11);
	
	aMutable->set(20);

	BOOST_CHECK_EQUAL(aProperty->get(), 11);

	graph.recompute();

	BOOST_CHECK_EQUAL(aProperty->get(), 21);
	}

BOOST_AUTO_TEST_CASE( test_brownian )
	{
	Graph graph;

	std::vector<boost::shared_ptr<Mutable<float> > > mutables;

	for (long k = 0; k < 20; k++)
		mutables.push_back(boost::shared_ptr<Mutable<float> >(new Mutable<float>()));

	for (long k = 0; k < mutables.size(); k++)
		mutables[k]->set(std::max(0.0, k - 5.0));

	std::vector<boost::shared_ptr<ComputedProperty<float> > > properties;

	for (long k = 0; k < mutables.size();k++)
		properties.push_back(
			bind(graph,
				boost::bind(&Mutable<float>::get, mutables[k])
				)
			);

	while (properties.size() != 1)
		{
		std::vector<boost::shared_ptr<ComputedProperty<float> > > newProps;
		for (long k = 0; k + 1 < properties.size(); k++)
			newProps.push_back(
				bind(graph, 
					boost::bind(
						brownian,
						properties[k],
						properties[k+1]
						)
					)
				);
		std::swap(properties, newProps);
		}

	BOOST_CHECK(properties[0]->get() == 0.0);

	graph.recompute();

	float initialVal = properties[0]->get();

	BOOST_CHECK(initialVal > 0);

	mutables[5]->set(100);

	long recomputeCount = graph.recompute();

	BOOST_CHECK_MESSAGE(
		recomputeCount > 50 && recomputeCount < 100, 
		"Expected recompute count < 100 but got " << recomputeCount
		);

	float updatedVal = properties[0]->get();

	BOOST_CHECK(updatedVal > initialVal);

	mutables[5]->set(0.0);

	graph.recompute();

	float finalVal = properties[0]->get();

	BOOST_CHECK(std::abs(finalVal - initialVal) < 0.0001);
	}

int sumMutables(boost::shared_ptr<Mutable<int> > lhs, boost::shared_ptr<Mutable<int> > rhs)
	{
	return lhs->get() + rhs->get();
	}


BOOST_AUTO_TEST_CASE( test_indices )
	{
	Graph graph;

	Index<std::pair<int, int>, int> index(graph);

	std::vector<boost::shared_ptr<Mutable<int> > > mutables;

	for (long k = 0; k < 10; k++)
		mutables.push_back(boost::shared_ptr<Mutable<int> >(new Mutable<int>()));

	std::vector<boost::shared_ptr<ComputedProperty<int> > > computations;
	for (long k = 0; k < 10; k++)
		for (long j = k; j < 10; j++)
			{
			computations.push_back(
				bind(graph, boost::bind(sumMutables, mutables[k], mutables[j]))
				);

			index.add(std::make_pair(k,j), computations.back());
			}

	graph.recompute();

	//verify that they all add to zero
	BOOST_CHECK_EQUAL(index.get(0).size(), 55);

	mutables[0]->set(1);

	graph.recompute();

	//now some don't add to zero
	BOOST_CHECK_EQUAL(index.get(0).size(), 45);
	BOOST_CHECK_EQUAL(index.get(1).size(), 9);
	BOOST_CHECK_EQUAL(index.get(2).size(), 1);

	//put it back and they do again
	mutables[0]->set(0);

	graph.recompute();

	BOOST_CHECK_EQUAL(index.get(0).size(), 55);

	//destroy some, and they are no longer in the index
	computations.resize(12);

	graph.recompute();

	BOOST_CHECK_EQUAL(index.get(0).size(), 12);
	}

BOOST_AUTO_TEST_SUITE_END( )



