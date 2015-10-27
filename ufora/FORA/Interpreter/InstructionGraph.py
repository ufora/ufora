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

import time

def reachableInstructions(rootInstruction):
    instructions = set()
    hashes = set()
    toCheck = [rootInstruction]

    while toCheck:
        i = toCheck.pop()
        if i not in instructions:
            instructions.add(i)
            hashes.add(i.hash)
            for index in range(i.flowsToCount()):
                toCheck.append(i.flowsTo(index))

    return instructions

def groupInstructionsByGraph(instructions):
    graphDict = {}

    for i in instructions:
        graph = i.graph

        if graph not in graphDict:
            graphDict[graph] = set()

        graphDict[graph].add(i)

    return graphDict

def drawInstructionGraph(instructions):
    import networkx as nx
    import matplotlib.pyplot as plt

    print "drawing graph with ", len(instructions)

    g = nx.DiGraph()

    def sizeForNode(i):
        if i.isRootInstruction():
            return 500
        else:
            return 100

    edgesToDraw = set()
    nodesToDraw = set()
    nodeColors = {}
    nodeSizes = {}

    def setNodeProps(i):
        if i.getTypedJumpTarget() is not None:
            nodeColors[i] = 'blue'
        elif i.getInstructionGroup().needsInterrupt(i):
            nodeColors[i] = 'green'
        if i.instructionBody.isJump():
            nodeSizes[i] = 100
        if i not in instructions:
            nodeColors[i] = 'red'
            nodeSizes[i] = 100


    def addEdge(i1, i2):
        clusteringWeight = .01
        edgeWeight = .05

        nodesToDraw.add(i1)
        nodesToDraw.add(i2)
        edgesToDraw.add((i1,i2))

        addRoots = i2 in instructions

        g.add_node(i1)
        g.add_node(i2)
        g.add_edge(i1, i2, weight = edgeWeight)

        if addRoots:
            g.add_node(i1.rootInstruction())
            g.add_node(i2.rootInstruction())

            g.add_edge(i1.rootInstruction(), i2.rootInstruction(), weight = 1.0)

            g.add_edge(i1, i1.rootInstruction(), weight = clusteringWeight)
            g.add_edge(i1.rootInstruction(), i1, weight = clusteringWeight)

            g.add_edge(i2, i2.rootInstruction(), weight = clusteringWeight)
            g.add_edge(i2.rootInstruction(), i2, weight = clusteringWeight)

        setNodeProps(i1)
        setNodeProps(i2)



    for i in instructions:
        for ix in range(i.flowsToCount()):
            flowsTo = i.flowsTo(ix)
            addEdge(
                i,
                flowsTo
                )

    pos = nx.spectral_layout(g)

    nx.draw_networkx_nodes(
        g,
        pos,
        nodelist = [n for n in g.nodes() if n in nodesToDraw],
        with_labels=False,
        node_size = [nodeSizes[n] if n in nodeSizes else 300 for n in g.nodes()],
        node_color = [nodeColors[n] if n in nodeColors else 'white' for n in g.nodes()],
        alpha = .5
        )

    nx.draw_networkx_edges(
        g,
        pos,
        edgelist = [e for e in g.edges() if e in edgesToDraw],
        alpha = .5
        )
    plt.show()

def checkInstructionGraphCycles(instructions):
    import networkx as nx

    g = nx.DiGraph()

    for i in instructions:
        g.add_node(i)

        for ix in range(i.flowsToCount()):
            flowsTo = i.flowsTo(ix)
            if flowsTo in instructions:
                g.add_edge(i, flowsTo)

    cycles = nx.simple_cycles(g)

    for c in cycles:
        if not checkCycleHasEntrypoint(c):
            print "************************************"
            print "No entrypoint in the following cycle: "
            for i in c:
                print i
                print "children:"
                for sub in i.children():
                    print "\t", repr(sub)
            print "************************************"
        else:
            print "************************************"
            print "cycle with ", len(c), " is OK"
            for i in c:
                if i.getTypedJumpTarget():
                    print "*** ",
                else:
                    print "    ",
                print repr(i)
            print "************************************"


def checkCycleHasEntrypoint(c):
    for i in c:
        if i.getTypedJumpTarget(): # i.isCompilerEntrypoint:
            return True
    return False

def allInstructionsOfAllVersions(instructionGraph, name):
    allGraphs = instructionGraph.graphs

    graphs = [g for g in allGraphs if g.graphName == name]

    allInstructions = set()

    def add(n):
        if n in allInstructions:
            return
        allInstructions.add(n)
        for s in n.children():
            add(s)

    print "there are ", len(graphs), " with name ", name

    for g in graphs:
        entryNode = instructionGraph.getRootInstruction(g, None)
        reachable = reachableInstructions(entryNode)

        for n in reachable:
            add(n)

    return allInstructions

if __name__ == '__main__':
    import fora
    fora.init_local()

    i = fora.eval('specialize(demos.MonteCarlo.MonteCarlo, `Member, `a_single_price)')

    if 1:
        print "Evaluating:"
        t0 = time.time()
        fora.eval('demos.MonteCarlo.MonteCarlo.a_single_price')
        print "done evaluating. took ", time.time() - t0

    instructions = reachableInstructions(i)
    graphs = groupInstructionsByGraph(instructions)

    graphsByName = dict([(g.graphName, g) for g in graphs])

    print len(instructions), " instructions"
    print len(graphs), " graphs: "

    #within the graph for 'price_once'
    #instructions = graphs[graphsByName['builtin.sum']]

    #checkInstructionGraphCycles(instructions)

    allSumInstructions = allInstructionsOfAllVersions(i.instructionGraph, 'builtin.sum')

    checkInstructionGraphCycles(allSumInstructions)

    #drawInstructionGraph(price_once)

