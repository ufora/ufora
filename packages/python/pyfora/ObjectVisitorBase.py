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

import pyfora.PyObjectNodes as PyObjectNodes


class ObjectVisitorBase(object):
    """
    ObjectVisitorInterface

    implementations are handed to PyObjectWalker's which
    calls relevant functions here based on the node type it
    visits. Only visits instances of PyObjectNodes.PyObjectNode.

    to override the behavior on nodes of a given type,
    add a method of the form `def visit_*(self, node): ... `

    This pattern is called an "extrinsic visitor".
    """
    def __init__(self):
        self._methodCache = dict()

    def visit_generic(self, _):
        pass

    def visit(self, node):
        if not isinstance(node, PyObjectNodes.PyObjectNode):
            return

        if hasattr(node, "__class__"):
            klass = node.__class__
            
            method = self._methodCache.get(klass, None)

            if method is None:
                methodName = "visit_" + node.__class__.__name__
                method = getattr(self, methodName, self.visit_generic)
                self._methodCache[klass] = method

            return method(node)


