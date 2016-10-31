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

import ufora.util.TypeAwareComparison as TypeAwareComparison

def pr(x):
    print x
    
class Graph(object):
    """common base class for graphs. Graphs have nodes, and labeled directed edges between nodes.
    
    graph implementations can store everything internally and provide a common interface to their internals
    """
    def __init__(self):
        self.watchers_ = set()
    def validNode(self, node):
        return False
    def hasEdge(self, nodeStart, nodeStop, label):
        return False
    
    def nodeProperty(self, node, attr):
        return None
    def setnodeProperty(self, node, attr, other):
        pass
    def desc(self, node):
        print 'Node<%ld>' % id(node)
    nodes = property(lambda self: set())
    def incomingEdges(self, node, label = None):
        return set()
    def outgoingEdges(self, node, label = None):
        return set()
    
    def addWatcher(self, watcher):
        self.watchers_.add(watcher)
    def removeWatcher(self, watcher):
        self.watchers_.remove(watcher)
    watchers = property(lambda self: set(self.watchers_))
    
class GraphWatcher(object):
    def __init__(self):
        pass
    
    def nodeToBeRemoved(self, node):
        pass
    def nodeAdded(self, node):
        pass
    def nodeDataChanged(self, node, oldData):
        pass
    def edgeToBeRemoved(self, edge):
        pass
    def edgeAdded(self, edge):
        pass

class EdgesIn_(object):
    def __init__(self, node):
        self.node_ = node
    def __getattr__(self, attr):
        if attr == 'node_':
            return self.__dict__[attr]
        return self.node_.graph_.incomingEdges(self.node_, attr)
    
class Node(object):
    def __init__(self, graph):
        object.__init__(self)
        self.__dict__['graph_'] = graph
    def __str__(self):
        return self.graph_.desc(self)
    def __repr__(self):
        return self.graph_.desc(self)
    def __getattr__(self, attr):
        if attr == 'edges_in':
            return EdgesIn_(self)
        
        if attr == 'graph':
            return self.graph_
        if attr[-1:] == '_':
            return self.__dict__[attr]
        return self.graph_.nodeProperty(self, attr)
    
    def __setattr__(self, attr, other):
        if attr == 'graph':
            self.graph_ = other
        
        if attr[-1:] == '_':
            self.__dict__[attr] = other
        else:
            self.graph_.setnodeProperty(self, attr, other)

class Edge(object):
    def __init__(self, graph, start, stop, label):
        self.graph_ = graph
        self.start_ = start
        self.stop_ = stop
        self.label_ = label
    
    graph = property(lambda self: self.graph_)
    start = property(lambda self: self.start_)
    stop = property(lambda self: self.stop_)
    label = property(lambda self: self.label_)
    
    tuple_ = property(lambda self: (self.graph_, self.start_, self.stop_, self.label_) )
    def __hash__(self):
        return hash(self.tuple_)
    def __cmp__(self, other):
        return TypeAwareComparison.typecmp(self, other, 
            lambda self, other : cmp(self.tuple_, other.tuple_))
    

