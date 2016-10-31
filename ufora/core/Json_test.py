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

class JsonTest(unittest.TestCase):
    def test_json_parse(self):
        self.assertValidParse("true", True)
        self.assertValidParse("false", False)
        self.assertValidParse("null", None)
        self.assertValidParse("0", 0)
        self.assertValidParse("1", 1)
        self.assertValidParse("2", 2)
        self.assertValidParse("[1,2,3,4]", (1,2,3,4))
        self.assertValidParse("'string'", 'string')
        self.assertValidParse("[]", ())
        self.assertValidParse("['string']", ('string',))
        self.assertValidParse("['string',2]", ('string',2))
        self.assertValidParse("['string',2, false]", ('string',2, False))
        self.assertValidParse("{'key':'val'}", {'key':'val'})
        self.assertValidParse("{'key':'val', 'key2':'val2'}", {'key':'val', 'key2':'val2'})
        self.assertValidParse("{}", {})

    def assertValidParse(self, stringForm, pyForm):
        #check that we can parse it
        json = Json.Json.parse(stringForm)

        #check that the stringification parses to the same thing
        self.assertEqual(Json.Json.parse(str(json)), json)

        #verify that is has the right simple form
        self.assertEqual(json.toSimple(), pyForm)

        #verify that it can be constructed from the simple form
        self.assertEqual(Json.Json.fromSimple(json.toSimple()), json)

    def test_json_repr_has_no_newlines(self):
        x = Json.Json([x for x in range(1000)])

        self.assertTrue("\n" in str(x))
        self.assertTrue("\n" not in repr(x), repr(x))

    def test_json_ordering(self):
        self.assertTrue(Json.Json([1]) < Json.Json([1,1]))
        self.assertTrue(Json.Json([1]) > Json.Json([0,1]))
        self.assertTrue(Json.Json([1]) > Json.Json([0]))
        self.assertTrue(Json.Json([1]) < Json.Json([2]))

        #everything sorts below 'None'
        self.assertTrue(Json.Json(1) < Json.Json(None))
        self.assertTrue(Json.Json([1]) < Json.Json(None))

    def test_json_hashing(self):
        j1 = Json.Json([1,2,3,4])
        j2 = Json.Json([1,2,3,4])
        j3 = Json.Json([1])

        self.assertEqual(j1.hash, j2.hash)
        self.assertTrue(j1.hash != j3.hash)

    def test_json_in_dicts(self):
        j1 = Json.Json([1,2,3,4])
        j2 = Json.Json(["haro"])
        j3 = Json.Json([1])

        self.assertEqual({j1:j2, j2:j3}, {j2:j3, j1:j2})

    def test_json_getitem(self):
        self.assertEqual(len(Json.Json(None)), 0)
        self.assertEqual(len(Json.Json(1)), 0)
        self.assertEqual(len(Json.Json("a")), 0)
        self.assertEqual(len(Json.Json(True)), 0)

        self.assertEqual(len(Json.Json(())), 0)
        self.assertEqual(len(Json.Json((1,))), 1)
        self.assertEqual(len(Json.Json((1,2))), 2)
        self.assertEqual(len(Json.Json({})), 0)
        self.assertEqual(len(Json.Json({'a':1})), 1)
        self.assertEqual(len(Json.Json({'a':1, 'b':2})), 2)

        j1 = Json.Json([1,2,3,4])
        j2 = Json.Json({'a':1, 'b':2})

        self.assertEqual(j1[0].toSimple(), 1)
        self.assertEqual(j1[1].toSimple(), 2)
        self.assertEqual(j1[2].toSimple(), 3)
        self.assertEqual(j1[3].toSimple(), 4)
        self.assertEqual([x.toSimple() for x in j1], [1,2,3,4])

        self.assertRaises(lambda: j1[-1])
        self.assertRaises(lambda: j1[4])
        self.assertRaises(lambda: j2['q'])

        self.assertEqual(j2['a'].toSimple(), 1)
        self.assertEqual(j2['b'].toSimple(), 2)

