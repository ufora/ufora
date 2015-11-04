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

import pyfora.ObjectVisitors as ObjectVisitors
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.ObjectVisitorBase as ObjectVisitorBase
import pyfora.ObjectRegistry as ObjectRegistry

import unittest


class TestVisitor1(ObjectVisitorBase.ObjectVisitorBase):
    def __init__(self):
        super(TestVisitor1, self).__init__()
        self.visitedValues = []

    def visit_generic(self, node):
        pass

    def visit_FunctionDefinition(self, node):
        self.visitedValues.append(node.pyObject.__name__)

    def visit_Primitive(self, node):
        self.visitedValues.append(str(node.pyObject))


class ClientObjectId(object):
    def __init__(self, value):
        self.value = value
    def __eq__(self, other):
        return self.value == other.value
    def __str__(self):
        return "ClientObjectId(%s)" % self.value
    def __repr__(self):
        return str(self)


class TestObjectRegistry(ObjectRegistry.ObjectRegistry):
    class Primitive(object):
        def __init__(self, value):
            self.value = value

    class FunctionDefinition(object):
        def __init__(self, sourceText, scope):
            self.sourceText = sourceText
            self.scope = scope

    def __init__(self):
        self.counter = 0
        self.objectMapping = dict()

    def allocateObject(self):
        tr = self.counter
        self.counter += 1
        return ClientObjectId(tr)

    def definePrimitive(self, objectId, value):
        self.objectMapping[objectId] = TestObjectRegistry.Primitive(value)

    def defineFunction(self, objectId, sourceText, scopeIds):
        self.objectMapping[objectId] = TestObjectRegistry.FunctionDefinition(
            sourceText, scopeIds
            )


class PyObjectWalkerTest(unittest.TestCase):
    def test_basic_walking(self):
        x = 2
        y = 3
        def f():
            return x + g()
        def g():
            return y + f() + h()
        def h():
            pass

        testVisitor = TestVisitor1()
        walker = PyObjectWalker.PyObjectWalker(testVisitor)

        walker.walkPyObject(f)

        self.assertEqual(
            set(testVisitor.visitedValues),
            set(['3', 'h', 'g', '2', 'f'])
            )

if __name__ == "__main__":
    unittest.main()

