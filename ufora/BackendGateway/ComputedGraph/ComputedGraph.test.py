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

import ufora.config.Setup as Setup
from ufora.BackendGateway.ComputedGraph.ComputedGraph import *
import unittest


class ComputedGraphTest(unittest.TestCase):
    def setUp(self):
        pass

    def testKeys(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        self.assert_(node.k1 == 20 and node.k2 == 25, "Keys do not have correct values")
        try:
            node.k1 = 31
        except:
            pass
        else:
            self.assert_(False, "Exception not thrown when attempting to change key values")
        self.assert_(node.k1 == 20 and node.k2 == 25, "Keys did not retain correct values")
        #testGraph.printListOfComputedProperties()

    def testMutableDefaults(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        self.assert_((node.v1 == 10) and (node.v2 == 20), "Mutables are not correctly set to default values")
        #testGraph.printListOfComputedProperties()

    def testProperty(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            def product(self):
                return self.v1*self.v2
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        self.assert_(node.product == node.v1 * node.v2, "Property does not return correct value")
        #testGraph.printListOfComputedProperties()
    def testChangeMutable(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            def product(self):
                return self.v1*self.v2
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        node.v1 = 15
        self.assert_(node.v1 == 15, "Mutable has the wrong value after attempting to change it")
        self.assert_(node.product == node.v1 * node.v2, "Property does not return correct value after changing mutable")
        #testGraph.printListOfComputedProperties()
    def testLocationAccess(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            def product(self):
                return self.v1*self.v2
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        node.v1 = 15
        with testGraph:
            node2 = X(k1 = 20, k2 = 25)
        self.assert_(node.v1 == node2.v1, "Accessing same location through different location references gives incorrect mutable values")
        self.assert_(node.v2 == node2.v2, "Accessing same location through different location references gives incorrect mutable values")
        self.assert_(node.product == node2.product, "Accessing same location through different location references gives incorrect property values")
        #testGraph.printListOfComputedProperties()
    def testFunction(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            @Function
            def testFunc(self, val):
                return val*self.v1 + self.v2
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        self.assert_(node.testFunc(3) == 3*node.v1 + node.v2, "Function returns the wrong value")
        node.v1 = 903
        node.v2 = -8
        self.assert_(node.testFunc(3) == 3*node.v1 + node.v2, "Function returns the wrong value after changing mutables")
        #testGraph.printListOfComputedProperties()
    def testInitializer(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            v3 = Mutable(int, lambda: 9)
            @Initializer
            def initialize(self):
                self.v3 = 200
        with testGraph:
            node = X(k1 = 21, k2 = 25)
        self.assert_(node.v3 == 200, "Initializer function did not set the value correctly")
        #testGraph.printListOfComputedProperties()
    def testCached(self):
        factor = 1
        val = 2
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            def product(self):
                return factor*self.v1*self.v2
        class Y(Location):
            k = Key()
            v = Mutable(X, lambda:  X(k1 = 0, k2 = 0))
            v2 = Mutable(int, lambda: 3)
            def	number(self):
                return self.v2*(self.v.v1 + self.v.v2) + val
        with testGraph:
            node = X(k1 = 20, k2 = 25)
            node2 = Y(k = 9)
        node2.v = node
        self.assert_(node.product == node.v1*node.v2, "First access to property gives the wrong value")
        self.assert_(node2.number == node2.v2*(node2.v.v1 + node2.v.v2) + val, "First access to property gives the wrong value")
        factor += 1
        val += 1
        self.assert_(node.product == node.v1*node.v2, "Property did not correctly return cached value")
        self.assert_(node2.number == node2.v2*(node2.v.v1 + node2.v.v2) + val - 1, "Property did not correctly return cached value")
        node.v1 = 90000
        self.assert_(node.product == factor*node.v1*node.v2, "After adjusting mutable, property was not recomputed")
        self.assert_(node2.number == node2.v2*(node2.v.v1 + node2.v.v2) + val, "After adjusting mutable, property was not recomputed")
        #testGraph.printListOfComputedProperties()
    def testNotCached(self):
        factor = 1.0
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            @NotCached
            def product(self):
                return factor*self.v1*self.v2
        with testGraph:
            node = X(k1 = 20, k2 = 25)
        self.assert_(node.product == factor*node.v1*node.v2, "Accessing NotCached property gives the wrong value")
        factor = 2.0
        self.assert_(node.product == factor*node.v1*node.v2, "NotCached property did not change from the previous value")
        #testGraph.printListOfComputedProperties()
    def testRootProperty(self):
        factor = 1
        val = 2
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            m = Mutable(int, lambda: 3)
            def product(self):
                return factor*self.k1*self.k2*self.m
        with testGraph:
            xNode1 = X(k1 = 30, k2 = 4)
        #testGraph.addRoot(xNode1, 'product')
        print "Computing product..."
        print xNode1.product
        print "done."
        print "Accessing product..."
        print xNode1.product
        print "Changing m..."
        xNode1.m = 22
        print "done."
        print "Recomputing product..."
        print xNode1.product
        print "done."
        #testGraph.printListOfComputedProperties()
    def testTemp(self):
        testGraph = ComputedGraph()
        class Z(Location):
            k1 = Key()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            v3 = Mutable(Location, lambda: Z(k1 = 20) )
            def product(self):
                return self.v1*self.v2
            def func(self):
                return self.product + self.v3.v2
        class Y(Location):
            k = Key()
            v = Mutable(X, lambda:  X(k1 = 0, k2 = 0))
            v2 = Mutable(int, lambda: 3)
            def	number(self):
                return self.v2*self.v.product
            def yfunc(self):
                return self.v.func*self.number
        with testGraph:
            node = X(k1 = 20, k2 = 25)
            node2 = Y(k = 9)
        node2.v = node
        node.v3 = node2

        print "node2.yfunc:", node2.yfunc
        node2.v2 = 9
        print "node2.yfunc:", node2.yfunc

        self.assert_(node.product == node.v1*node.v2, "First access to property gives the wrong value")
        self.assert_(node2.number == node2.v2*node2.v.product, "First access to property gives the wrong value")
        print node2.number
        node.v1 = 15
        print node2.number
        self.assert_(node2.number == node2.v2*node2.v.product, "After adjusting mutable, property was not recomputed")
        print "UP/DOWN TEST"
        print "Up from Y number:", node2.propUp("number")
        print "Down from X v1:", node.propDown("v1")
        print "Up from X product:", node.propUp("product")
        print "UP/DOWN TEST DONE"
        print "Depth 2 prop up from number"
        l = node2.propUp("number")
        print "Level 1:", l
        for l2 in l:
            print "Level 2 from", l2, "is", l2[0].propUp(l2[2])
        #testGraph.printListOfComputedProperties()
    # make sure it is dirtying, orphaning, deleting correctly
    def testOrphan(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            def product(self):
                return self.v1*self.v2
        class Y(Location):
            k = Key()
            v = Mutable(X, lambda:  X(k1 = 0, k2 = 0))
            v2 = Mutable(int, lambda: 3)
            def	number(self):
                return self.v2*self.v.product
        with testGraph:
            nodeX1 = X(k1 = 20, k2 = 25)
            nodeX2 = X(k1 = 21, k2 = 26)
            nodeY = Y(k = 10)
        nodeX1.v1 = 11
        nodeX2.v2 = 12
        nodeY.v = nodeX1
        print nodeY.number
        print "CHANGING"
        nodeY.v = nodeX2
        print nodeY.number
        #testGraph.printListOfComputedProperties()
    def testLocKey(self):
        testGraph = ComputedGraph()
        class X(Location):
            k1 = Key()
            k2 = Key()
            v1 = Mutable(int, lambda: 10)
            v2 = Mutable(int, lambda: 20)
            v3 = Mutable(dict, lambda: dict())
            def product(self):
                print "self =", self
                return self.v1*self.v2
            def func2(self):
                print "self =", self
                return 1.0*self.product
            def func3(self):
                print "self =", self
                return 1.0*self.func2
        class Y(Location):
            v = Key() #X(k1 = 0, k2 = 0) # Key which holds LocRef
            v2 = Mutable(int, lambda: 3)
            v3 = Mutable(str, lambda: str(''))
            def	number(self):
                return self.v2*self.v.func3

        with testGraph:
            nodeX1 = X(k1 = 20, k2 = 25)
            nodeX1.v3 = {'h':1, 'e':2, 'l':3, 'p':4}
            nodeY = Y(v = nodeX1)
        print nodeY.number
        print "CHANGING"
        nodeX1.v1 = 11
        print nodeY.number
        #testGraph.printListOfComputedProperties()
    def testLocKey2(self):
        testGraph = ComputedGraph()
        class Chr(Location):
            strIn = Key()
            chrVal = Key()
            def position(self):
                d = {}
                for s in range(len(self.strIn.v3)):
                    d[self.strIn.v3[s]] = s
                return d[self]

        class Str(Location):
            k1 = Key()
            v3 = Mutable(list, lambda: list())
            @Function
            def setString(self, strText):
                v = list()
                for i in range(len(strText)):
                    v.append(Chr(strIn = self, chrVal = strText[i]))
                self.v3 = v
            def getStr(self):
                #print self.v3
                s = ''
                for i in range(len(self.v3)):
                    s += self.v3[i].chrVal
                return s

        with testGraph:
            testStr = Str(k1 = 20)
        print "Setting string"
        testStr.setString("hello")
        print "Printing string"
        print testStr.getStr
        #print "Reprinting string"
        #print testStr.getStr
        #print "Reprinting string again"
        #print testStr.getStr
        print "position:", testStr.v3[2].position
        #print "position again:", testStr.v3[2].position
        #print "char:", testStr.v3[2].chrVal
        print "Setting string"
        testStr.setString("some other string")
        print "Printing string"
        print testStr.getStr
        #testGraph.printListOfComputedProperties()

    # note - have onupdate test

    def testCreate(self):
        testGraph = ComputedGraph()
        def thing(x):
            print "thing called for onUpdate"
        class X(Location):
            k = Key()
            v = Mutable(int, lambda: 8, onUpdate = thing)
            u = 9000
            @Function
            def testFunc(self, x):
                print 'here is testFunc'
                print 'testFunc has self.v =', self.v
                print 'testFunc has x =', x
                print 'testFunc returning', self.v + x
                return self.v + x
            @NotCached
            def testNC(self):
                return self.k*4
        with testGraph:
            n = X(k = 902)
            pass

        print "inital value: n.v =", n.v
        print "about to change value.."
        n.v = 33
        print "n.v =", n.v

        print "Accessing key.."
        print "n.k =", n.k

        print "testing func:", n.testFunc(-3)
        print n.testNC
        print n.u # 'passing class member on directly'


def executeTestAsMain():
    with Setup.PushSetup(Setup.defaultSetup()):
        #tests = ['testKeys', 'testMutableDefaults', 'testProperty', 'testChangeMutable', 'testLocationAccess', 'testFunction', 'testInitializer', 'testCached', 'testNotCached', 'testRootProperty']
        #tests = ['testProperty']
        tests = ['testTemp']
        #tests = ['testOrphan']
        #tests = ['testLocKey2']
        #tests = ['testKeys']
        #tests = ['testCreate']
        suite = unittest.TestSuite(map(ComputedGraphTest, tests))
        unittest.TextTestRunner().run(suite)


if __name__ == '__main__':
    executeTestAsMain()

