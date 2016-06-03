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
#ifndef GraphUtil_hppml_
#define GraphUtil_hppml_

/*******
GraphUtil

utilities for doing computations on graphs whose nodes and edges
are defined using sets and maps.

********/

#include <set>
#include <map>

#include <boost/config.hpp>
#include <boost/graph/graph_traits.hpp>
#include <boost/graph/adjacency_list.hpp>
#include <boost/graph/strong_components.hpp>
#include <boost/property_map/property_map.hpp>

#include "../cppml/CPPMLPrettyPrinter.hppml"
#include "../containers/TwoWaySetMap.hpp"

namespace  GraphUtil {

/********

Computes the set of edges reachable from a particular node in a directed graph.

It is not necessary for every node to be a key in inEdges. If it's not there,
but it's referred to by another edge, the algorithm assumes it has no outgoing
edges.

*********/
template<class T>
void	computeReachableNodes(
					const std::map<T, std::set<T> >& inEdges,
					std::set<T>& outReachable,
					const T& inNode
					)
	{
	if (outReachable.find(inNode) == outReachable.end())
		{
		outReachable.insert(inNode);

		auto map_it = inEdges.find(inNode);

		if (map_it != inEdges.end())
			for (auto edge: map_it->second)
				computeReachableNodes(inEdges, outReachable, edge);
		}
	}

template<class T>
void	computeReachableNodes(
					const TwoWaySetMap<T, T>& inEdges,
					std::set<T>& outReachable,
					const T& inNode
					)
	{
	computeReachableNodes(inEdges.getKeysToValues(), outReachable, inNode);
	}

/*****

Find, in the directed graph "inEdges", every group of nodes such that
each node is reachable from each of the others by a path.  Essentially,
two nodes are in a group together iff there is a cycle that contains them.

nodes that aren't in the edge map don't ever show up in the graph

if includeSingleNodeComponents is set to true, then we include everything.
If it's set to false, we filter out nodes that are not themselves part of
any cycle.

If onlyIncludeFreeComponents is set to true, then we don't include any
subgroups that have external nodes jumping into them.

*****/
template<class T>
void	computeStronglyConnectedComponents(
				const std::map<T, std::set<T> >& inEdges,
				std::vector<std::set<T> >& outComponents,
				bool includeSingleNodeComponents,
				bool onlyIncludeFreeComponents
				)
	{
	if (!inEdges.size())
		return;
	using namespace boost;
	using namespace std;

	map<T, uint32_t> 				nodeToIndex;
	map<uint32_t, T> 				indexToNode;

	uint32_t ix = 0;
	for (typename map<T, set<T> >::const_iterator
			it = inEdges.begin(); it!= inEdges.end(); ++it)
		{
		nodeToIndex[it->first] = ix;
		indexToNode[ix] = it->first;
		ix++;
		}

	typedef adjacency_list<vecS, vecS, bidirectionalS> Graph;

	Graph g(nodeToIndex.size());

	//add any edges that stay within the graph
	for (typename map<T, set<T> >::const_iterator
			node_it = inEdges.begin(); node_it != inEdges.end(); ++node_it)
		for (typename set<T>::const_iterator edge_it = node_it->second.begin();
											edge_it != node_it->second.end();
											++edge_it)
			{
			typename map<T, uint32_t>::iterator  index_it =
					nodeToIndex.find(*edge_it);

			if (index_it != nodeToIndex.end())
				add_edge(nodeToIndex[node_it->first], index_it->second, g);
			}

	map<int, int>	components;

	boost::associative_property_map< std::map<int, int> >
		  components_prop_map(components);

	int totalComponents = strong_components(g, components_prop_map);

	outComponents.resize(totalComponents);
	for (map<int,int>::iterator  it = components.begin();
											it != components.end(); ++it)
		{
		lassert(it->second >= 0 && it->second < totalComponents);
		outComponents[it->second].insert(indexToNode[it->first]);
		}

	if (onlyIncludeFreeComponents)
		{
		set<int> badComponents;

		//for each edge, check which components are being crossed and mark
		//destination components as 'bad' when they're different

		for (long k = 0; k < outComponents.size();k++)
			for (typename set<T>::const_iterator it = outComponents[k].begin();
					it != outComponents[k].end(); ++it)
				{
				const T& node = *it;

				int componentIndex = components[nodeToIndex[node]];

				typename map<T, set<T> >::const_iterator edgeIt = inEdges.find(node);

				for (typename set<T>::const_iterator
							outgoing_it = edgeIt->second.begin();
							outgoing_it != edgeIt->second.end();
							++outgoing_it
							)
					{
					int destComponentIndex = components[nodeToIndex[*outgoing_it]];
					if (componentIndex != destComponentIndex)
						badComponents.insert(destComponentIndex);
					}
				}
		for (long k = 0; k < outComponents.size();k++)
			if (badComponents.find(k) != badComponents.end())
				{
				std::swap(outComponents[k], outComponents.back());
				outComponents.resize(outComponents.size() - 1);
				k--;
				}
		}
	if (!includeSingleNodeComponents)
		for (long k = 0; k < outComponents.size();k++)
			if (outComponents[k].size() == 1)
				{
				const T& node = *outComponents[k].begin();

				typename map<T, set<T> >::const_iterator it = inEdges.find(node);

				bool mapsToSelf = (it != inEdges.end() &&
								it->second.find(node) != it->second.end());

				if (!mapsToSelf)
					{
					std::swap(outComponents[k], outComponents.back());
					outComponents.resize(outComponents.size() - 1);
					k--;
					}
				}
	}


template<class T>
void	computeStronglyConnectedComponents(
				const TwoWaySetMap<T, T>& inEdges,
				std::vector<std::set<T> >& outComponents,
				bool includeSingleNodeComponents,
				bool onlyIncludeFreeComponents
				)
	{
	computeStronglyConnectedComponents(
		inEdges.getKeysToValues(),
		outComponents,
		includeSingleNodeComponents,
		onlyIncludeFreeComponents
		);
	}

}





#endif

