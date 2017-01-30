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

import pyfora.PureImplementationMappings as PureImplementationMappings
from pyfora.PythonObjectRehydrator import PythonObjectRehydrator
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry
import pyfora.PyObjectWalker as PyObjectWalker

import unittest
import struct
import tempfile


class PythonObjectRehydratorTest(unittest.TestCase):
    def setUp(self):
        self.mappings = PureImplementationMappings.PureImplementationMappings()

    def get_encoded_string_and_id(self, toConvert):
        binaryObjectRegistry = BinaryObjectRegistry.BinaryObjectRegistry()

        walker = PyObjectWalker.PyObjectWalker(
            self.mappings,
            binaryObjectRegistry
            )

        objId = walker.walkPyObject(toConvert)

        binaryObjectRegistry.defineEndOfStream()

        return binaryObjectRegistry.str(), objId

    def roundTripConvert_string(self, toConvert, allowUserCodeModuleLevelLookups=True):
        encodedString, objId = self.get_encoded_string_and_id(toConvert)

        rehydrator = PythonObjectRehydrator(self.mappings,
                                            allowUserCodeModuleLevelLookups)

        return rehydrator.convertEncodedStringToPythonObject(encodedString, objId)

    def roundTripConvert_file(self, toConvert, allowUserCodeModuleLevelLookups=True):
        encodedString, objId = self.get_encoded_string_and_id(toConvert)

        rehydrator = PythonObjectRehydrator(self.mappings,
                                            allowUserCodeModuleLevelLookups)

        with tempfile.TemporaryFile() as fp:
            fp.write(encodedString + struct.pack("<q", objId))
            fp.seek(0)

            return rehydrator.readFileDescriptorToPythonObject(fp.fileno())

    def check_rehydration(self, toConvert, allowUserCodeModuleLevelLookups=True):
        rehydrated_by_string = self.roundTripConvert_string(
            toConvert,
            allowUserCodeModuleLevelLookups=allowUserCodeModuleLevelLookups
            )

        self.assertEqual(toConvert, rehydrated_by_string)

        rehydrated_by_file = self.roundTripConvert_file(
            toConvert,
            allowUserCodeModuleLevelLookups=allowUserCodeModuleLevelLookups
            )        

        self.assertEqual(toConvert, rehydrated_by_file)

    def test_rehydration_primitives(self):
        self.check_rehydration(1)
        self.check_rehydration(2.0)
        self.check_rehydration(None)
        self.check_rehydration("nel mezzo del cammin di nostra vita")
        self.check_rehydration(True)

    def test_rehydration_lists_1(self):
        self.check_rehydration(range(100))
        self.check_rehydration([float(elt) for elt in range(65)])
        self.check_rehydration([1,2,3,4,5,6.0,7.0,8.0,9.0])
        self.check_rehydration([[1,2,3], [4.0, 5.0], [[]]])

    def test_rehydration_lists_2(self):
        self.check_rehydration([[1]])

    def test_rehydration_dicts(self):
        d = {1:2, 3:4, 5:"fda", (6,7): [1,2,3], "asdf": [1,2,[3,4]]}
        self.check_rehydration(d)
        
    def test_rehydration_tuples(self):
        self.check_rehydration((1,2,3.0,"four"))
        self.check_rehydration((1,(2,)))
        self.check_rehydration((1,2,3.0,"four",(5,(6,7))))

if __name__ == '__main__':
    unittest.main()
