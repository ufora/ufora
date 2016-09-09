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


class DictTestCases(object):
    """Test cases for pyfora dicts"""

    def test_returnDict(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f():
            return x

        self.equivalentEvaluationTest(f, comparisonFunction=lambda x, y: x == y)

    def test_dicts(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        def f(key):
            return x[key]

        for key in x:
            self.equivalentEvaluationTest(f, key)

    def test_dict_keys(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        self.equivalentEvaluationTest(
            lambda: x.keys(),
            comparisonFunction=lambda x, y: set(x) == set(y)
            )

    def test_dict_values(self):
        x = { 1: 2, 3: 4, 5: 6, 7: 8, 9: 10, 11: 12 }

        self.equivalentEvaluationTest(
            lambda: x.values(),
            comparisonFunction=lambda x, y: set(x) == set(y)
            )

    def test_dict_creation_1(self):
        x = [(1,2), (3,4)]

        def f():
            return dict(x)

        self.equivalentEvaluationTest(
            f,
            comparisonFunction=lambda x, y: x == y
            )

    def test_dict_creation_2(self):
        def f():
            return { x: x**2 for x in range(10) if x % 2 != 0 }

        self.equivalentEvaluationTest(
            f,
            comparisonFunction=lambda x, y: x == y
            )

    def test_dict_iteration(self):
        def f():
            d = {1: 2}
            return [val for val in d]

        self.equivalentEvaluationTest(f)
