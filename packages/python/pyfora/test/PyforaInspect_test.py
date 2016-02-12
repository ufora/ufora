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

import pyfora.PyforaInspect as PyforaInspect
import unittest

class PyforaInspectTest(unittest.TestCase):
    def test_pyforaInspect_twoNestedClasses(self):
        def f1():
            class C1:
                def fC1(self):
                    return 0
            return C1

        def f2():
            class C1:
                def fC2(self):
                    return 1
            return C1

        with self.assertRaises(PyforaInspect.PyforaInspectError) :
            PyforaInspect.getsourcelines(f1()().__class__)

    def test_pyforaInspect_twoClassesOneName(self):
        class C2:
            def fC1(self):
                return 0

        def f2():
            class C2:
                def fC2(self):
                    return 1
            return C2

        with self.assertRaises(PyforaInspect.PyforaInspectError) :
            PyforaInspect.getsourcelines(f2()().__class__)

    def test_pyforaInspect_twoClassestwoNames(self):
        def f1():
            class C3a:
                def fC1(self):
                    return 0
            return C3a

        def f2():
            class C3b:
                def fC2(self):
                    return 1
            return C3b

        self.assertNotEqual(
            PyforaInspect.getsourcelines(f1()().__class__),
            PyforaInspect.getsourcelines(f2()().__class__)
            )


if __name__ == "__main__":
    unittest.main()
