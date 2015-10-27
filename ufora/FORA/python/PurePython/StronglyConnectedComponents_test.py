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

import unittest
import ufora.native.Json as Json
import pickle
import pyfora.StronglyConnectedComponents as StronglyConnectedComponents
import numpy

class StronglyConnectedComponentsTest(unittest.TestCase):
    def testComponents(self):
        for nodeCount in range(2,5):
            for passIx in range(100):
                graph = {}
                for n in range(nodeCount):
                    graph[n] = []

                edges = []
                for ix1 in range(nodeCount):
                    for ix2 in range(nodeCount):
                        if ix1 != ix2:
                            edges.append((ix1,ix2))

                numpy.random.seed(passIx)
                numpy.random.shuffle(edges)

                for ix1, ix2 in edges:
                    graph[ix1].append(ix2)
                    self.validateGraph(graph)

    def validateGraph(self, graph):
        components = StronglyConnectedComponents.stronglyConnectedComponents(graph)

        #print "************"
        #print graph
        #print components

        levels = {}
        for ix in range(len(components)):
            for c in components[ix]:
                levels[c] = ix

        def reachable(x):
            dirty = set([x])
            reachable = set([])
            while dirty:
                node = dirty.pop()
                if node not in reachable:
                    reachable.add(node)
                    for downstream in graph[node]:
                        dirty.add(downstream)
            return reachable

        for n in graph:
            r = reachable(n)
            
            for reachableChild in r:
                self.assertTrue(levels[n] >= levels[reachableChild], (n,levels[n],reachableChild,levels[reachableChild]))

            for child in graph[n]:
                if n in reachable(child):
                    self.assertTrue(levels[child] == levels[n])
                else:
                    self.assertTrue(levels[child] < levels[n])




