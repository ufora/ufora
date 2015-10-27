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

import pyfora.PyAstUtil as PyAstUtil
import pyfora.Exceptions as Exceptions
import ast
import unittest


class PyAstUtilTest(unittest.TestCase):
    def test_computeDataMembers_1(self):
        class C:
            def __init__(self, x):
                self.x = x
                self.y = x ** 2.0

        dataMembers = PyAstUtil.computeDataMembers(C)
            
        self.assertEqual(
            dataMembers,
            set(['x', 'y'])
            )

    def test_computeDataMembers_2(self):
        class C2:
            def __init__(self, x):
                if x > 0:
                    self.x = x
                

        dataMembers = PyAstUtil.computeDataMembers(C2)
        
        # in our translation, we're _always_ producing an x member
        self.assertEqual(
            dataMembers,
            set(['x'])
            )

    def test_computeDataMembers_3(self):
        class C3:
            def __init__(self):
                self.x = self.y = 0

        dataMembers = PyAstUtil.computeDataMembers(C3)

        self.assertEqual(
            dataMembers,
            set(['x', 'y'])
            )

    def test_computeDataMembers_4(self):
        class C4:
            def __init__(self, arg):
                (self.x, self.y), self.z = arg

        dataMembers = PyAstUtil.computeDataMembers(C4)

        self.assertEqual(
            dataMembers,
            set(['x', 'y', 'z'])
            )

    def test_computeDataMembers_error_1(self):
        class E1:
            def __init__():
                self.x = 0

        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstUtil.computeDataMembers(E1)

    def test_computeDataMembers_error_2(self):
        class E2:
            def __init__(*args):
                self.x = 0

        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstUtil.computeDataMembers(E2)

    def test_computeDataMembers_error_3(self):
        class E3:
            def __init__(self):
                self.x = 0
                def f(x):
                    return x

        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstUtil.computeDataMembers(E3)

    def test_computeDataMembers_error_4(self):
        class E4:
            def __init__(self):
                self.x = 0
                class c(object):
                    def __init__(self):
                        self.z = 0

        with self.assertRaises(Exceptions.PythonToForaConversionError):
            PyAstUtil.computeDataMembers(E4)

