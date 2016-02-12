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

import pyfora.PureImplementationMappings as PureImplementationMappings
import pyfora.PureImplementationMapping as PureImplementationMapping
import pyfora.PyObjectWalker as PyObjectWalker
import pyfora.NamedSingletons as NamedSingletons

import unittest

class SomeRandomInstance:
    pass

class PureUserWarning:
    pass

class PyObjectWalkerTest(unittest.TestCase):
    def test_cant_provide_mapping_for_named_singleton(self):
        mappings = PureImplementationMappings.PureImplementationMappings()

        #empty mappings work
        PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=None
            )

        mappings.addMapping(
            PureImplementationMapping.InstanceMapping(
                SomeRandomInstance(), SomeRandomInstance
                )
            )

        #an instance mapping doesn't cause an exception
        PyObjectWalker.PyObjectWalker(
            purePythonClassMapping=mappings,
            objectRegistry=None
            )

        self.assertTrue(UserWarning in NamedSingletons.pythonSingletonToName)

        mappings.addMapping(
            PureImplementationMapping.InstanceMapping(UserWarning, PureUserWarning)
            )

        #but this mapping doesnt
        with self.assertRaises(Exception):
            PyObjectWalker.PyObjectWalker(
                purePythonClassMapping=mappings,
                objectRegistry=None
                )


if __name__ == "__main__":
    unittest.main()
