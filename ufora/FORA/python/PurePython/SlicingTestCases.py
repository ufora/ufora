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


class SlicingTestCases(object):
    """Test cases for pyfora slicing"""

    def test_custom_slicing_1(self):
        class ListWrapper_1:
            def __init__(self, m):
                self.m = m
            def __getitem__(self, maybeSlice):
                if isinstance(maybeSlice, slice):
                    return self.m[maybeSlice]
                return -100000

        def f():
            l = ListWrapper_1(range(10))
            return (l[1:4], l[:3], l[:], l[::], l[3:], l[4::2], l[4])

        self.equivalentEvaluationTest(f)

    def test_custom_slicing_2(self):
        class ListWrapper_2:
            def __init__(self, m):
                self.m = m
            def __getitem__(self, maybeSlice):
                if isinstance(maybeSlice, slice):
                    return self.m[maybeSlice]
                if isinstance(maybeSlice, tuple):
                    return [self.m[bla] for bla in maybeSlice]
                return -100000

        def f():
            l = ListWrapper_2(range(10))
            return l[:, 1:4, 3:9]

        self.equivalentEvaluationTest(f)

    def test_returning_slice_1(self):
        def f1():
            return slice

        self.equivalentEvaluationTest(f1)

    def test_inserting_slice_1(self):
        def f():
            s = slice(1,2,3)
            x = range(10)
            return x[s]

        self.equivalentEvaluationTest(f)
