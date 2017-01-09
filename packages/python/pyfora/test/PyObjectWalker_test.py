#   Copyright 2016 Ufora Inc.
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

from pyfora.BinaryObjectRegistry import BinaryObjectRegistry
import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PureImplementationMapping as PureImplementationMapping
from pyfora.PyObjectWalker import PyObjectWalker
import pyfora.NamedSingletons as NamedSingletons

import ast
import gc
import unittest


class SomeRandomInstance:
    pass


class PureUserWarning:
    pass


class PyObjectWalkerTest(unittest.TestCase):
    def setUp(self):
        self.excludeList = ["staticmethod", "property", "__inline_fora"]

        def is_pureMapping_call(node):
            return isinstance(node, ast.Call) and \
                isinstance(node.func, ast.Name) and \
                node.func.id == 'pureMapping'

        self.excludePredicateFun = is_pureMapping_call

        self.mappings = PureImplementationMappings.PureImplementationMappings()
    
    def test_cant_provide_mapping_for_named_singleton(self):
        #empty mappings work
        PyObjectWalker(
            self.mappings,
            BinaryObjectRegistry()
            )

        self.mappings.addMapping(
            PureImplementationMapping.InstanceMapping(
                SomeRandomInstance(), SomeRandomInstance
                )
            )

        #an instance mapping doesn't cause an exception
        PyObjectWalker(
            self.mappings,
            BinaryObjectRegistry()
            )

        self.assertTrue(UserWarning in NamedSingletons.pythonSingletonToName)
    
    def test_PyObjectWalker_TypeErrors(self):
        mappings = PureImplementationMappings.PureImplementationMappings()

        with self.assertRaises(TypeError):
            not_an_objectregistry = 2
            PyObjectWalker(mappings, not_an_objectregistry)

    def test_PyObjectWalker_refcount_on_objectRegistry(self):
        walker = PyObjectWalker(
            self.mappings,
            BinaryObjectRegistry()
            )

        # just check that the folling calls succeeed (see github #289
        gc.collect()
        walker.walkPyObject(1)
        
    def test_PyObjectWalker_boto_connection(self):
        import boto

        conn = boto.connect_s3()

        walker = PyObjectWalker(
            self.mappings,
            BinaryObjectRegistry()
            )

        # just check that this doesn't fail
        walker.walkPyObject(conn)

if __name__ == "__main__":
    unittest.main()

