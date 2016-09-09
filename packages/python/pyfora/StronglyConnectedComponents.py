#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

# adapted from http://www.logarithmic.net/pfh-files/blog/01208083168/tarjan.py
# implements Tarjan's strongly connected components algorithm.

# Recall: two nodes in a (directed) graph are called _strongly connected_
# if there exists a (directed) path from each node to the other node.
# This forms an equivalence relation on a graph, and the equivalence
# classes are the _strongly connected components_ (SCC) of the graph. Note
# that SCC are not quite the same thing as cycles, as cycles can only
# hit individual nodes at most once.

# also note that the list of SCC returned by Tarjan's algorithm give a
# reverse topological sort of the DAG of SCC.

def stronglyConnectedComponents(graph):
    """
    `graph` here is a dict from keys (of some hashable class) to a list of keys
    """
    indexCounter = [0]
    stack = []
    lowLinks = {}
    index = {}
    result = []

    def strongConnect(node):
        index[node] = indexCounter[0]
        lowLinks[node] = indexCounter[0]
        indexCounter[0] += 1
        stack.append(node)

        try:
            successors = graph[node]
        except:
            successors = []
        for successor in successors:
            if successor not in lowLinks:
                # Successor has not yet been visited; recurse on it
                strongConnect(successor)
                lowLinks[node] = min(lowLinks[node], lowLinks[successor])
            elif successor in stack:
                # the successor is in the stack and hence in the current SCC
                lowLinks[node] = min(lowLinks[node], index[successor])

        # If `node` is a root node, pop the stack and generate an SCC
        if lowLinks[node] == index[node]:
            connectedComponent = []

            while True:
                successor = stack.pop()
                connectedComponent.append(successor)
                if successor == node:
                    break
            component = tuple(connectedComponent)
            result.append(component)

    for node in graph:
        if node not in lowLinks:
            strongConnect(node)

    return result

