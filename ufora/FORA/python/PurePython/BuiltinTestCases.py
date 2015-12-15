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

import pyfora
import pyfora.Exceptions


class BuiltinTestCases(object):
    def test_range_builtin_simple(self):
        def f(x):
            return range(x)

        self.equivalentEvaluationTest(f, 10)

    def test_range_builtin_overloads(self):
        def f(start, stop, incr=1):
            return range(start, stop, incr)

        self.equivalentEvaluationTest(f, 1, 10)
        self.equivalentEvaluationTest(f, 10, 5)
        self.equivalentEvaluationTest(f, 5, 10)
        self.equivalentEvaluationTest(f, 10, 1, 2)
        self.equivalentEvaluationTest(f, 10, 5, 5)
        self.equivalentEvaluationTest(f, 10, 10, 10)

    def test_ord_chr_builtins(self):
        def f():
            chars = [chr(val) for val in range(40, 125)]
            vals = [ord(val) for val in chars]
            return (chars, vals)

        self.equivalentEvaluationTest(f)

    def test_builtins_abs(self):
        def f(x):
            return abs(x)
        for x in range(-10, 10):
            self.equivalentEvaluationTest(f, x)

        self.equivalentEvaluationTest(f, True)
        self.equivalentEvaluationTest(f, False)
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, [])
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, ["test"])
        with self.assertRaises(pyfora.ComputationError):
            self.evaluateWithExecutor(f, "test")

    def test_builtins_all(self):
        def f(x):
            return all(x)
        self.equivalentEvaluationTest(f, [])
        self.equivalentEvaluationTest(f, [True])
        self.equivalentEvaluationTest(f, [False])
        self.equivalentEvaluationTest(f, [True, True])
        self.equivalentEvaluationTest(f, [True, False])
        self.equivalentEvaluationTest(f, [False, True])
        self.equivalentEvaluationTest(f, [False, False])

    def test_builtins_any(self):
        def f(x):
            return any(x)
        self.equivalentEvaluationTest(f, [])
        self.equivalentEvaluationTest(f, [True])
        self.equivalentEvaluationTest(f, [False])
        self.equivalentEvaluationTest(f, [True, True])
        self.equivalentEvaluationTest(f, [True, False])
        self.equivalentEvaluationTest(f, [False, True])
        self.equivalentEvaluationTest(f, [False, False])

    def test_builtins_zip_not_implemented(self):
        def f(x):
            return zip(x)
        with self.assertRaises(pyfora.Exceptions.PyforaNotImplementedError):
            self.equivalentEvaluationTest(f, [])

    def test_reversed_builtins(self):
        def f():
            a = [1, 2, 3, 4, 5, 6]
            b = reversed(a)
            toReturn = []
            for v in b:
                toReturn = toReturn + [v]
            return toReturn

        self.equivalentEvaluationTest(f)

    def test_reduce_builtin(self):
        def mul(x,y): return x*y
        def sub(x,y): return x-y
        self.equivalentEvaluationTest(lambda: reduce(mul, [1,2,3,4,5]))
        self.equivalentEvaluationTest(lambda: reduce(mul, [1,2,3,4,5], 0))

        def nonparallel(x):
            for v in x:
                yield v

        self.equivalentEvaluationTest(lambda: reduce(sub, nonparallel([1.0,2.0,3.0,4.0,5.0])))
        self.equivalentEvaluationTest(lambda: reduce(sub, nonparallel([1.0,2.0,3.0,4.0,5.0]), 10))

    def test_map_builtin(self):
        def addOne(x):
            return x + 1
        self.equivalentEvaluationTest(lambda: map(None, [1,2,3]))
        self.equivalentEvaluationTest(lambda: map(addOne, [1,2,3]))
        self.equivalentEvaluationTest(lambda: map(addOne, (x for x in [1,2,3])))

    def test_supported_builtin_member(self):
        import math
        def f(x):
            return x + math.pi

        self.equivalentEvaluationTest(f, 2)

    def test_unsupported_builtin_member(self):
        import math
        def f(x):
            return math.sin(x)

        with self.assertRaises(pyfora.Exceptions.PythonToForaConversionError):
            self.equivalentEvaluationTest(f, 2)

