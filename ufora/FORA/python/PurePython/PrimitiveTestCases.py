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


class PrimitiveTestCases(object):
    """Test cases for pyfora primitives"""

    def test_compute_float(self):
        def f():
            return 1.5

        remote = self.evaluateWithExecutor(f)
        self.assertEqual(f(), remote)
        self.assertTrue(isinstance(remote, float))

    def test_compute_nothing(self):
        def f():
            return None

        remote = self.evaluateWithExecutor(f)
        self.assertIs(f(), remote)


    def test_primitives_know_they_are_pyfora(self):
        def testFun():
            x = 10
            return x.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))


    def test_boolean_conversion(self):
        class HasBoolConversion:
            def __init__(self, x):
                self.x = x

            def __nonzero__(self):
                return bool(self.x)

        class HasNoBoolConversion:
            pass

        candidates = [
            0, 1,
            0.0, 1.0,
            "", "string",
            False, True,
            lambda x:x,
            HasBoolConversion(0),
            HasBoolConversion(1),
            HasNoBoolConversion(),
            None,
            (), (1,), (3,4),
            [], [1], [1,2],
            {}, {1:2}, {1:2, 3:4},
            bool, type(None)
            ]

        self.equivalentEvaluationTest(lambda : [bool(c) for c in candidates])
        self.equivalentEvaluationTest(lambda : [True if c else False for c in candidates])


    def test_operator_pos_neg_invert(self):
        class HasPos:
            def __pos__(self):
                return 1

        class HasNeg:
            def __neg__(self):
                return 1

        class HasInvert:
            def __invert__(self):
                return 1

        class HasNothing:
            pass

        candidates = [
            0, 1, -1,
            0.0, 1.0,
            "string",
            False, True,
            lambda x:x,
            HasPos(),
            HasNeg(),
            HasInvert(),
            HasNothing(),
            None, (), [], {}, bool
            ]

        for c in candidates:
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: +x, c)
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: -x, c)
            self.equivalentEvaluationTestThatHandlesExceptions(lambda x: ~x, c)


    def test_negate_int(self):
        with self.create_executor() as executor:
            def f(): return -10
            self.equivalentEvaluationTest(f)


    def test_ints(self):
        def f():
            x = 100
            return x

        self.equivalentEvaluationTest(f)

    def test_ints_1(self):
        def f():
            return 42

        self.equivalentEvaluationTest(f)

    def test_ints_2(self):
        def f():
            return 2 == 2

        self.equivalentEvaluationTest(f)

    def test_floats_1(self):
        def f():
            return 42.0

        self.equivalentEvaluationTest(f)

    def test_bools_1(self):
        def f():
            return True

        self.equivalentEvaluationTest(f)

    def test_complex(self):
        self.equivalentEvaluationTest(lambda: abs(complex(1.0,0.0) * complex(1.0,0.0)))
