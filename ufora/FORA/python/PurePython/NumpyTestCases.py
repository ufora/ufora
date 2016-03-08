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

import numpy
import numpy.testing
import random
import time


class NumpyTestCases(object):
    @staticmethod
    def compareButDontCheckTypes(x, y):
        if isinstance(x, basestring) and isinstance(y, basestring):
            return x == y

        if hasattr(x, '__len__') and hasattr(y, '__len__'):
            l1 = len(x)
            l2 = len(y)
            if l1 != l2:
                return False
            for idx in range(l1):
                if not NumpyTestCases.compareButDontCheckTypes(x[idx], y[idx]):
                    return False
            return True
        else:
            return x == y

    def test_numpy(self):
        n = numpy.zeros(10)
        def f():
            return n.shape
        self.equivalentEvaluationTest(f)

    def test_empty_array_ctor(self):
        def f():
            return numpy.array([])

        self.equivalentEvaluationTest(f)

    def test_repeated_array_ctor(self):
        x = numpy.array([[1,2],[3,4]])
        def f():
            return numpy.array(x)

        self.equivalentEvaluationTest(f)

    def test_numpy_pinverse_2(self):
        numpy.random.seed(42)

        def f(array):
            return numpy.linalg.pinv(array)

        arr = numpy.random.rand(20, 10) * 1000
        t1 = time.time()
        r1 = self.evaluateWithExecutor(f, arr)
        t2 = time.time()
        r2 = f(arr)
        t3 = time.time()
        print t3 - t2, t2 - t1
        self.assertArraysAreAlmostEqual(r1, r2)

    def test_numpy_pinverse_1(self):
        def f(arr):
            array = numpy.array(arr)
            return numpy.linalg.pinv(array)

        arr1 = [ [67.0, 63.0, 87.0],
                [77.0, 69.0, 59.0],
                [85.0, 87.0, 99.0],
                [15.0, 17.0, 19.0] ]

        r1 = self.evaluateWithExecutor(f, arr1)
        r2 = f(arr1)
        self.assertArraysAreAlmostEqual(r1, r2)

        arr2 = [ [1.0, 1.0, 1.0, 1.0],
            [5.0, 7.0, 7, 9] ]
        r1 = self.evaluateWithExecutor(f, arr2)
        r2 = f(arr2)
        self.assertArraysAreAlmostEqual(r1, r2)

    def test_numpy_transpose(self):
        def f():
            array = numpy.array([ [67.0, 63.0, 87.0],
                [77.0, 69.0, 59.0],
                [85.0, 87.0, 99.0],
                [15.0, 17.0, 19.0] ])

            return array.transpose()
        self.equivalentEvaluationTest(f)


        def f2():
            arr = numpy.array([[[67.0], [87.0]], [[69.0], [85.0]], [[69.0], [15.0]]])

            return arr.transpose()
        self.equivalentEvaluationTest(f2)


        def f3():
            arr = numpy.array([1.0, 2.0, 3.0, 4.0, 5.0])

            return arr.transpose()
        self.equivalentEvaluationTest(f3)

    def test_numpy_indexing_1(self):
        def f():
            array = numpy.array([ [67.0, 63.0, 87.0],
                [77.0, 69.0, 59.0],
                [85.0, 87.0, 99.0],
                [15.0, 17.0, 19.0] ])

            toReturn = []
            l = len(array)
            l2 = len(array[0])
            for x in range(l):
                for y in range(l2):
                    toReturn = toReturn + [array[x][y]]
            return toReturn

        self.equivalentEvaluationTest(
            f, comparisonFunction=NumpyTestCases.compareButDontCheckTypes
            )

    def test_numpy_indexing_2(self):
        def f():
            arr = numpy.array([ 67.0, 63.0, 87.0, 77.0, 69.0, 59.0, 85.0, 87.0, 99.0 ])
            return (arr, arr[0], arr[1], arr[8])

        self.equivalentEvaluationTest(
            f, comparisonFunction=NumpyTestCases.compareButDontCheckTypes
            )

    def test_numpy_indexing_3(self):
        def f():
            arr = numpy.array([[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]])
            return (arr, arr[0], arr[1], arr[1][0], arr[0][1][1])
        self.equivalentEvaluationTest(
            f, comparisonFunction=NumpyTestCases.compareButDontCheckTypes)

        def f2():
            arr = numpy.array([[[67.0], [87.0]], [[69.0], [85.0]], [[69.0], [15.0]]])
            return (arr, arr[0], arr[1], arr[1][0], arr[2][1][0])

        self.equivalentEvaluationTest(
            f2, comparisonFunction=NumpyTestCases.compareButDontCheckTypes)

        def f3():
            arr = numpy.array([[[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]], \
                               [[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]]])
            return (arr, arr[0], arr[1], arr[1][0], arr[0][1][1], arr[0][1][1][1])

        self.equivalentEvaluationTest(
            f3, comparisonFunction=NumpyTestCases.compareButDontCheckTypes)

    def test_return_numpy(self):
        n = numpy.zeros(10)
        def f():
            return n
        res = self.evaluateWithExecutor(f)

        self.assertTrue(isinstance(res, numpy.ndarray), res)

        self.equivalentEvaluationTest(f)

    def test_numpy_flatten(self):
        def f(lists):
            b = numpy.array(lists)
            return b.flatten()
        a = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        self.equivalentEvaluationTest(f, a)

        b = [[67.0, 63, 87],
               [77, 69, 59],
               [85, 87, 99],
               [79, 72, 71],
               [63, 89, 93],
               [68, 92, 78]]
        self.equivalentEvaluationTest(f, b)

        c = [[[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]], \
             [[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]]]

        self.equivalentEvaluationTest(f, c)

    def test_numpy_arrays_are_iterable(self):
        def f():
            array = numpy.array([[67, 63, 87],
               [77, 69, 59],
               [85, 87, 99],
               [79, 72, 71],
               [63, 89, 93],
               [68, 92, 78]])
            toReturn = []
            for val in array:
                toReturn = toReturn + [val]
            return toReturn

        self.equivalentEvaluationTest(f)

    def test_numpy_tolist(self):
        def f(lists):
            b = numpy.array(lists)
            return b.tolist()
        a = [1, 2, 3, 4, 5, 6]
        self.equivalentEvaluationTest(f, a)

        b = [[67, 63, 87],
             [77, 69, 59],
             [85, 87, 99],
             [79, 72, 71],
             [63, 89, 93],
             [68, 92, 78]]
        self.equivalentEvaluationTest(f, b)

        c = [[[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]], \
             [[[67.0, 63.0], [87.0, 77.0]], [[69.0, 59.0], [85.0, 87.0]]]]
        self.equivalentEvaluationTest(f, c)

    def test_numpy_dot_product_1a(self):
        random.seed(43)

        listLength = 20
        def f(arr1, arr2):
            return numpy.dot(arr1, arr2)

        for _ in range(10):
            x1 = [random.uniform(-10, 10) for _ in range(0, listLength)]
            x2 = [random.uniform(-10, 10) for _ in range(0, listLength)]

            self.equivalentEvaluationTest(
                f, x1, x2,
                comparisonFunction=numpy.isclose
                )

    def test_numpy_dot_product_1b(self):
        random.seed(43)

        listLength = 20
        def f(arr1, arr2):
            return arr1.dot(arr2)

        for _ in range(10):
            x1 = numpy.array([
                random.uniform(-10, 10) for _ in range(0, listLength)])
            x2 = [random.uniform(-10, 10) for _ in range(0, listLength)]

            self.equivalentEvaluationTest(
                f, x1, x2,
                comparisonFunction=numpy.isclose
                )

    def test_numpy_dot_product_2a(self):
        random.seed(44)

        listLength = 20

        arr1 = [random.uniform(-10, 10) for _ in range(0, listLength)]
        arr2 = [random.uniform(-10, 10) for _ in range(0, listLength)]

        def f():
            a = numpy.array(arr1)
            b = numpy.array(arr2)

            return numpy.dot(a, b)

        r1 = self.evaluateWithExecutor(f)
        r2 = f()

        numpy.testing.assert_allclose(r1, r2)

    def test_numpy_dot_product_2b(self):
        random.seed(44)

        listLength = 20

        arr1 = [random.uniform(-10, 10) for _ in range(0, listLength)]
        arr2 = [random.uniform(-10, 10) for _ in range(0, listLength)]

        def f():
            a = numpy.array(arr1)
            b = numpy.array(arr2)

            return a.dot(b)

        r1 = self.evaluateWithExecutor(f)
        r2 = f()

        numpy.testing.assert_allclose(r1, r2)

    def test_numpy_dot_product_3a(self):
        def f():
            m1 = numpy.array([1.0, 2, 3, 4, 5, 6])
            m2 = numpy.array([[67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78]])
            return numpy.dot(m1, m2)
        self.equivalentEvaluationTest(f)

    def test_numpy_dot_product_3b(self):
        def f():
            m1 = numpy.array([1.0, 2, 3, 4, 5, 6])
            m2 = numpy.array([[67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78]])
            return m1.dot(m2)
        self.equivalentEvaluationTest(f)

    def test_numpy_dot_product_4a(self):
        def f():
            m1 = numpy.array([1.0, 2, 3])
            m2 = numpy.array([[67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78]])
            return numpy.dot(m2, m1)
        self.equivalentEvaluationTest(f)

    def test_numpy_dot_product_4b(self):
        def f():
            m1 = numpy.array([1.0, 2, 3])
            m2 = numpy.array([[67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78]])
            return numpy.dot(m2, m1)
        self.equivalentEvaluationTest(f)

    def test_numpy_dot_product_4c(self):
        def f():
            m1 = [1.0, 2, 3]
            m2 = numpy.array([[67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78]])
            return numpy.dot(m2, m1)
        self.equivalentEvaluationTest(f)

    def test_numpy_dot_product_5a(self):
        x = numpy.array([[1,2],[3,4]])
        y = numpy.array([1,2,3])

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    numpy.dot(y, x)

    def test_numpy_dot_product_5a(self):
        x = numpy.array([[1,2],[3,4]])
        y = numpy.array([1,2,3])

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    numpy.dot(y, x)

    def test_numpy_dot_product_5b(self):
        x = numpy.array([[1,2],[3,4]])
        y = numpy.array([1,2,3])

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    y.dot(x)

    def test_numpy_matrix_multiplication_1a(self):
        def f():
            m1 = numpy.array([ [67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78] ])
            m2 = m1.transpose()

            return numpy.dot(m1, m2)
        r1 = self.evaluateWithExecutor(f)
        r2 = f()
        self.assertArraysAreAlmostEqual(r1, r2)

    def test_numpy_matrix_multiplication_1b(self):
        def f():
            m1 = numpy.array([ [67.0, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78] ])
            m2 = m1.transpose()

            return numpy.dot(m1, m2)
        r1 = self.evaluateWithExecutor(f)
        r2 = f()
        self.assertArraysAreAlmostEqual(r1, r2)

    def test_numpy_matrix_multiplication_misaligned_1(self):
        m1 = numpy.array([[1,2], [3,4]])
        m2 = numpy.array([[1,2], [3,4], [5,6]])

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    numpy.dot(m1, m2)

    def test_numpy_matrix_multiplication_misaligned_2(self):
        m1 = numpy.array([1,2, 3,4])
        m2 = numpy.array([[1,2], [3,4], [5,6]])

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    numpy.dot(m1, m2)

    def test_numpy_reshape(self):
        def f(newShape):
            m1 = numpy.array([
                [67.0, 63, 87],
                [77, 69, 59],
                [85, 87, 99],
                [79, 72, 71],
                [63, 89, 93],
                [68, 92, 78] ])
            return m1.reshape(newShape)

        self.equivalentEvaluationTest(f, (1, 18))
        self.equivalentEvaluationTest(f, (2, 9))
        self.equivalentEvaluationTest(f, (3, 6))
        self.equivalentEvaluationTestThatHandlesExceptions(f, (1, 1))

    def test_numpy_matrix_division(self):
        random.seed(44)

        matrix = numpy.array([ [67, 63, 87],
                       [77, 69, 59],
                       [85, 87, 99],
                       [79, 72, 71],
                       [63, 89, 93],
                       [68, 92, 78] ])

        for _ in range(10):
            def f(x):
                return matrix / x
            self.equivalentEvaluationTest(f, random.uniform(-10, 10))

            def f2(x):
                return matrix * x
            self.equivalentEvaluationTest(f2, random.uniform(-10, 10))

            def f3(x):
                return matrix + x
            self.equivalentEvaluationTest(f3, random.uniform(-10, 10))

            def f4(x):
                return matrix - x
            self.equivalentEvaluationTest(f4, random.uniform(-10, 10))

            def f5(x):
                return matrix ** x
            self.equivalentEvaluationTest(f5, random.uniform(-10, 10))

    def test_numpy_make_array(self):
        def f():
            return numpy.zeros(10)

        self.equivalentEvaluationTest(f)

    def test_numpy_addition_1(self):
        def f():
            x1 = numpy.array([[1,2],[3,4]])
            x2 = numpy.array([[8,7],[6,5]])

            return x1 + x2

        self.equivalentEvaluationTest(f)

    def test_numpy_binary_ops(self):
        def f():
            x1 = numpy.array([[1,2],[3,4]])
            x2 = numpy.array([[8,7],[6,5]])

            return (x1 / x2) ** 2 - x2 ** x2

        self.equivalentEvaluationTest(f)

    def test_numpy_addition_2(self):
        def f():
            x1 = numpy.array([[1,2],[3,4]])
            x2 = numpy.array([[8,7,5,6]])

            return x1 + x2

        with self.assertRaises(ValueError):
            with self.create_executor() as fora:
                with fora.remotely:
                    f()

    def test_numpy_arange(self):

        def f():
            return numpy.arange(-1,.9,.2)
        r1 = self.evaluateWithExecutor(f)
        r2 = f()
        self.assertArraysAreAlmostEqual(r1, r2)

    def test_numpy_zeros_1(self):
        def f():
            return numpy.zeros((10, 2))

        self.equivalentEvaluationTest(f)

    def test_numpy_zeros_2(self):
        def f():
            return numpy.zeros(10)

        self.equivalentEvaluationTest(f)

    def test_numpy_linsolve_1(self):
        a = numpy.array([[-2.0, 3.0], [4.0, 7.0]])
        b = numpy.array([[1.0], [2.0]])

        def f():
            return numpy.linalg.solve(a, b)

        self.equivalentEvaluationTest(f)

    def test_numpy_linsolve_2(self):
        a = numpy.array([[-2.0, 3.0], [-2.0, 3.0]])
        b = numpy.array([[1.0], [2.0]])

        def f():
            return numpy.linalg.solve(a, b)

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except:
            # just see that we get an exception here without dying.
            # we're not wrapping the numpy linalg errors yet
            pass

    def test_numpy_linsolve_3(self):
        a = numpy.array([[-2.0, 3.0], [4.0, 7.0]])
        b = numpy.array([1.0, 2.0])

        def f():
            return numpy.linalg.solve(a, b)

        self.equivalentEvaluationTest(f)

    def test_numpy_slicing_1(self):
        size = 3
        def f(lowIx, highIx):
            x = numpy.array(range(size))
            return x[lowIx:highIx]

        for ix in range(size):
            for jx in range(size):
                self.equivalentEvaluationTest(f, ix, jx)

    def test_numpy_eq(self):
        x = numpy.array([1,2,3])
        y = numpy.array([1,0,2])
        def f():
            return x == y

        self.equivalentEvaluationTest(f)

    def test_numpy_isnan(self):
        def f(x):
            return [numpy.isnan(elt) for elt in x]

        vals = [1, 2.0, numpy.nan, numpy.inf, -numpy.nan]
        numpy.testing.assert_allclose(
            f(vals),
            self.evaluateWithExecutor(f, vals)
            )

    def test_numpy_isinf(self):
        def f(x):
            return [numpy.isnan(elt) for elt in x]

        vals = [1, 2.0, numpy.nan, numpy.inf, -numpy.nan]
        numpy.testing.assert_allclose(
            f(vals),
            self.evaluateWithExecutor(f, vals)
            )

    def check_svd(self, x):
        def svd(a):
            return numpy.linalg.svd(a)

        pyforaRes = self.evaluateWithExecutor(svd, x)
        numpyRes = svd(x)

        self.assertEqual(len(pyforaRes), len(numpyRes))

        for ix in xrange(len(pyforaRes)):
            numpy.testing.assert_allclose(
                pyforaRes[ix],
                numpyRes[ix]
                )

    def test_svd_1(self):
        self.check_svd(numpy.array([[1,3],[2,4]]))

    def test_isinstance_on_remote(self):
        from pyfora.pure_modules.pure_numpy import PurePythonNumpyArray

        with self.create_executor() as ufora:
            with ufora.remotely:
                a = numpy.array([[1,2],[3,4]])

            with ufora.remotely.downloadAll():
                res = isinstance(a, PurePythonNumpyArray)

            self.assertTrue(res)

    def test_norm_1(self):
        def f(x):
            return numpy.linalg.norm(x)

        x = numpy.array([1,2,3,4])

        self.assertEqual(
            f(x),
            self.evaluateWithExecutor(f, x)
            )

        x = x.reshape((2,2))

        self.assertEqual(
            f(x),
            self.evaluateWithExecutor(f, x)
            )
