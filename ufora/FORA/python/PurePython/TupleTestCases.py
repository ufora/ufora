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


import numpy.testing


class TupleTestCases(object):
    """Test cases for pyfora tuples"""

    def test_tuple_str(self):
        t1 = (2,2)
        self.equivalentEvaluationTest(
            lambda: str(t1)
            )

    def test_len_on_tuple(self):
        def f():
            a = (9,)
            b = ()
            c = (1,2,4)
            return (len(a), len(b), len(c))

        self.evaluateWithExecutor(f)


    def test_tuple_eq_ne_1(self):
        t1 = (2,2)
        t2 = (1,4)

        self.equivalentEvaluationTest(
            lambda: (t1 == t2, t1 != t2)
            )

    def test_tuple_eq_ne_2(self):
        t1 = (2,2)
        t2 = t1

        self.equivalentEvaluationTest(
            lambda: (t1 == t2, t1 != t2)
            )

    def test_tuple_conversion(self):
        def f(x):
            return (x,x+1)

        self.equivalentEvaluationTest(f, 10)

    def test_tuples_1(self):
        tup = (1, 2, 3)

        def f(ix):
            return tup[ix]

        for ix in range(-3, 3):
            self.equivalentEvaluationTest(f, ix)


    def test_tuples_are_pyfora_objects(self):
        def f():
            return (1,2,3).__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(f))


    def test_pyTuples_1(self):
        def f(ix):
            t = (1,2,3)
            return t[ix]

        for ix in range(-3,3):
            self.equivalentEvaluationTest(f, ix)

    def test_pyTuples_3(self):
        def f(elt):
            t = (1,2,3)
            return t.index(elt)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)


    def test_returningTuples_1(self):
        def returningATuple_1():
            return (0, 1)

        self.equivalentEvaluationTest(returningATuple_1)

    def test_returningTuples_2(self):
        def returningATuple_2():
            return 0, 1

        self.equivalentEvaluationTest(returningATuple_2)


    def test_tuple_assignment(self):
        def f():
            x,y = 1,2
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_larger(self):
        def f():
            x,y = 1,2,3
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_smaller(self):
        def f():
            x,y,z = 1,2
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield(self):
        def f():
            def it():
                yield 1
                yield 2
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield_larger(self):
        def f():
            def it():
                yield 1
                yield 2
                yield 3
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_from_yield_smaller(self):
        def f():
            def it():
                yield 1
            x,y = it()
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_nested(self):
        def f():
            x,(y,z) = (1,(2,3))
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_assignment_nested_2(self):
        def f():
            x,(y,z) = (1,[2,3])
            return (x,y)

        self.equivalentEvaluationTestThatHandlesExceptions(f)

    def test_tuple_unpack_in_loop(self):
        def func():
            f = lambda x: x+1
            g = lambda x: x+2
            res = 0
            for ct in xrange(1000000000):
                res = res + f(ct)
                f,g = g,f
            return res

        #this should take forever if compilation of tuple assignment
        #is not working correctly
        self.evaluateWithExecutor(func)

    def test_tuple_lt(self):
        tups = [
            (), (1,), (2,), (0,), (1,2), (1,3), (1,1), (2,2), (0,2),
            (1,2,3), (2,1,4)
            ]

        def compare_some_tuples():
            return [(t1, t2, t1 < t2) for t1 in tups for t2 in tups]

        numpy.testing.assert_array_equal(
            compare_some_tuples(),
            self.evaluateWithExecutor(compare_some_tuples)
            )

    def test_tuple_gt(self):
        tups = [
            (), (1,), (2,), (0,), (1,2), (1,3), (1,1), (2,2), (0,2),
            (1,2,3), (2,1,4)
            ]

        def compare_some_tuples():
            return [(t1, t2, t1 > t2) for t1 in tups for t2 in tups]

        numpy.testing.assert_array_equal(
            compare_some_tuples(),
            self.evaluateWithExecutor(compare_some_tuples)
            )

        
