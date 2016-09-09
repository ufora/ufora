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
import ufora.config.Config as Config

class ConfigTest(unittest.TestCase):
    def test_bool_conversion(self):
        self.assertTrue(Config.parseBool(True))
        self.assertTrue(Config.parseBool("1"))
        self.assertTrue(Config.parseBool("100"))
        self.assertTrue(Config.parseBool("T"))
        self.assertTrue(Config.parseBool("TRUE"))
        self.assertTrue(Config.parseBool("True"))

        self.assertFalse(Config.parseBool(False))
        self.assertFalse(Config.parseBool(""))
        self.assertFalse(Config.parseBool("0"))
        self.assertFalse(Config.parseBool("F"))
        self.assertFalse(Config.parseBool("FALSE"))
        self.assertFalse(Config.parseBool("False"))

        with self.assertRaises(ValueError):
            Config.parseBool("this is clearly not a bool")

