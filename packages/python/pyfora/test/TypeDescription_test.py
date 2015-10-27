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
import json
import pyfora.TypeDescription as TypeDescription

class TypeDescriptionTest(unittest.TestCase):
    def test_simple_serialization_and_deserialization(self):
        typeDescription = TypeDescription.Primitive(23.4)
        self.assertDeserializationSerializationSucceeded(typeDescription)

        typeDescription = TypeDescription.Tuple([1, 2, 3, 4, 5])
        self.assertDeserializationSerializationSucceeded(typeDescription)

        typeDescription = TypeDescription.ClassDefinition("source text here", ['test'])
        self.assertDeserializationSerializationSucceeded(typeDescription)

    def test_nested_type_serialization_and_deserialization(self):
        dict1 = { "a": 1, "b": 2, "c": 3}
        dict2 = { "a": 4, "b": 5, "c": 6}

        typeDescription = TypeDescription.ClassDefinition("source text here", [dict1, dict2])
        self.assertDeserializationSerializationSucceeded(typeDescription)

    def assertDeserializationSerializationSucceeded(self, typeDescription):
        jsonString = json.dumps(typeDescription)
        jobject = json.loads(jsonString)

        deserializationResult = TypeDescription.fromList(jobject)
        self.assertNamedTuplesAreTheSame(deserializationResult, typeDescription)

    def assertNamedTuplesAreTheSame(self, t1, t2):
        dict1 = t1._asdict()
        dict2 = t2._asdict()
        keys1 = dict1.keys()
        keys2 = dict2.keys()
        self.assertEqual(len(keys1), len(keys2))
        for key in keys1:
            self.assertEqual(dict1[key], dict2[key])

    def deserialize(self, objectDefinition):
        self.assertTrue(hasattr(objectDefinition, 'typeName'))
        return TypeDescription.deserialize(objectDefinition)

if __name__ == "__main__":
    unittest.main()

