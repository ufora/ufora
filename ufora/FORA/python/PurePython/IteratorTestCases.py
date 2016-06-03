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

import pyfora.Exceptions as Exceptions


class IteratorTestCases(object):
    def test_xrange_builtin_simple(self):
        def f(x):
            toReturn = 0
            for ix in xrange(x):
                toReturn = ix + toReturn
            return toReturn
        self.equivalentEvaluationTest(f, 10)

    def test_sum_xrange(self):
        with self.create_executor() as executor:
            arg = 1000000000
            def f():
                return sum(xrange(arg))

            self.assertEqual(self.evaluateWithExecutor(f), arg*(arg-1)/2)

    def test_iterate_split_xrange(self):
        def f():
            g = xrange(100).__pyfora_generator__().split()[0]
            res = []
            for x in g:
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_split_mapped_xrange(self):
        def f():
            g = xrange(100).__pyfora_generator__().map(lambda x:x).split()[0]
            res = []
            for x in g:
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_map_split_xrange(self):
        for _ in range(10):
            def f():
                g = xrange(100).__pyfora_generator__().split()[0].map(lambda x:x)
                res = []
                for x in g:
                    res = res + [x]

                return res == range(50)

            self.assertTrue(self.evaluateWithExecutor(f))


    def test_iterate_xrange(self):
        def f():
            res = []

            for x in xrange(50):
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_xrange_generator(self):
        def f():
            res = []

            for x in xrange(50).__pyfora_generator__().map(lambda x:x):
                res = res + [x]

            return res == range(50)

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_iterate_xrange_empty(self):
        def f():
            res = []

            for x in xrange(0):
                res = res + [x]

            return res == []

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_on_xrange(self):
        for ct in [0,1,2,4,8,16,32,64,100,101,102,103]:
            self.equivalentEvaluationTest(lambda: sum(x for x in xrange(ct)))
            self.equivalentEvaluationTest(lambda: list(x for x in xrange(ct)))
            self.equivalentEvaluationTest(lambda: [x for x in xrange(ct)])

    def test_GeneratorExp_works(self):
        self.equivalentEvaluationTest(lambda: list(x for x in xrange(10)))

    def test_sum_on_generator(self):
        class Generator1:
            def __pyfora_generator__(self):
                return self

            def __init__(self, x, y, func):
                self.x = x
                self.y = y
                self.func = func

            def __iter__(self):
                yield self.func(self.x)

            def isNestedGenerator(self):
                return False

            def canSplit(self):
                return self.x + 1 < self.y

            def split(self):
                if not self.canSplit():
                    return None

                return (
                    Generator1(self.x, (self.x+self.y)/2, self.func),
                    Generator1((self.x+self.y)/2, self.y, self.func)
                    )

            def map(self, mapFun):
                newMapFun = lambda x: mapFun(self.func(x))
                return Generator1(self.x, self.y, newMapFun)

        def f():
            return sum(Generator1(0, 100, lambda x:x))

        self.assertEqual(f(), 0)
        self.assertEqual(self.evaluateWithExecutor(f), sum(xrange(100)))

    def test_list_generators_splittable(self):
        def f():
            return [1,2,3].__pyfora_generator__().canSplit()

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_list_generators_mappable(self):
        def f():
            return list([1,2,3].__pyfora_generator__().map(lambda z:z*2)) == [2,4,6]

        self.assertTrue(self.evaluateWithExecutor(f))

    def test_return_generator_object_throws_exception(self):
        def f():
            def yields(ct):
                yield ct
            return yields(10)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.ForaToPythonConversionError as e:
            self.assertIsInstance(e.message, str)

    def test_list_on_iterable(self):
        def it(x):
            while x > 0:
                yield x
                x = x - 1

        def f1():
            return list(xrange(10))

        def f2():
            return list(it(10))

        self.equivalentEvaluationTest(f1)
        self.equivalentEvaluationTest(f2)


    def test_iterable_is_pyfora_object(self):
        def it(x):
            while x > 0:
                yield x
                x = x - 1

        def f():
            return it(10).__is_pyfora__

        self.assertIs(self.evaluateWithExecutor(f), True)


    def test_iteration_1(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.equivalentEvaluationTest(iteration_1)


    def test_iteration_2(self):
        def iteration_1():
            x = [0,1,2,3]
            tr = 0
            for val in x:
                tr = tr + val
            return tr

        self.equivalentEvaluationTest(iteration_1)


    def test_empty_iterator(self):
        def sequence(ct):
            while ct > 0:
                yield ct
                ct = ct - 1

        class EmptyIterator:
            @staticmethod
            def staticSequence(ct):
                while ct > 0:
                    yield ct
                    ct = ct - 1

            def sequence(self, ct):
                while ct > 0:
                    yield ct
                    ct = ct - 1

        self.equivalentEvaluationTest(lambda: list(sequence(1)))

        for count in [0,1,2]:
            self.equivalentEvaluationTest(lambda: list(sequence(count)))
            self.equivalentEvaluationTest(lambda: list(EmptyIterator.staticSequence(count)))
            self.equivalentEvaluationTest(lambda: list(EmptyIterator().sequence(count)))

    def test_custom_iterators_1(self):
        class C_5771(object):
            def __init__(self, m):
                self.m = m
            def __getitem__(self, ix):
                return self.m[ix]
            def __iter__(self):
                for val in self.m:
                    yield val ** 2.0

        def f(c):
            return [val for val in c]

        self.equivalentEvaluationTest(f, C_5771(range(5)))

    def test_custom_iterators_2(self):
        class C_5772(object):
            def __init__(self, m):
                self.m = m
            def __getitem__(self, ix):
                return self.m[ix]

        def f(c):
            return [val for val in c]

        self.equivalentEvaluationTest(f, C_5772(range(5)))

    def test_custom_iterators_3(self):
        class C_5773(object):
            def __getitem__(self, ix):
                if ix < 10:
                    return ix * 2
                raise IndexError

        def f(c):
            return [val for val in c]

        self.equivalentEvaluationTest(f, C_5773())

    def test_custom_iterators_4(self):
        class C_5774(object):
            def __getitem__(self, ix):
                if ix < 10:
                    return ix * 2
                raise IndexError()

        def f(c):
            return [val for val in c]

        self.equivalentEvaluationTest(f, C_5774())

