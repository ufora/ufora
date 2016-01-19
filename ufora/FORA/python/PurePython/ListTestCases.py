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
import pyfora.Exceptions as Exceptions

class ListTestCases(object):
    """Test cases for pyfora lists"""

    def test_handle_empty_list(self):
        def f():
            return []
        self.equivalentEvaluationTest(f)


    def test_list_str(self):
        t1 = (2,2)
        self.equivalentEvaluationTest(
            lambda: str(t1)
            )


    def test_return_list(self):
        def f():
            return [1, 2, 3, 4, 5]

        self.equivalentEvaluationTest(f)


    def test_list_in_loop(self):
        def f(ct):
            ix = 0
            l = []
            while ix < ct:
                l = l + [ix]
                ix = ix + 1

            res = 0
            for e in l:
                res = res + e
            return res

        ct = 1000000
        res = self.evaluateWithExecutor(f, ct)
        self.assertEqual(res, ct * (ct-1) / 2)

    def test_list_getitem_1(self):
        def f():
            l = [1,2,3]

            return l[0]

        self.equivalentEvaluationTest(f)

    def test_list_getitem_2(self):
        v = [1,2,3]
        def f(ix):
            return v[ix]

        for ix in range(-3,3):
            self.equivalentEvaluationTest(f,ix)

    def test_list_getitem_3(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.equivalentEvaluationTest(nestedLists)

    def test_list_len(self):
        def f():
            l = [1,2,3]

            return (len(l), len(l) == 3, len(l) is 3)

        self.equivalentEvaluationTest(f)

    def test_lists_3(self):
        def f(elt):
            x = [1,2,3]
            return x.index(elt)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)

    def test_lists_6(self):
        v = [1,2,3]
        def f(val):
            return v.index(val)

        for ix in range(1, 4):
            self.equivalentEvaluationTest(f, ix)


    def test_list_bound_methods_know_they_are_pyfora(self):
        def testFun():
            return [].__add__.__is_pyfora__

        self.assertTrue(self.evaluateWithExecutor(testFun))


    def test_listComprehensions_1(self):
        def listComprehensions_1():
            aList = [0,1,2,3]
            aList = [elt * 2 for elt in aList]
            return aList[-1]

        self.equivalentEvaluationTest(listComprehensions_1)

    def test_listComprehensions_2(self):
        def listComprehensions_2(arg):
            aList = range(4)
            filteredList = [elt for elt in aList if elt % 2 == 0]
            return filteredList[arg]

        for ix in range(-2, 2):
            self.equivalentEvaluationTest(listComprehensions_2, ix)

    def test_listComprehensions_3(self):
        def listComprehensions_3():
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[1][0]

        self.equivalentEvaluationTest(listComprehensions_3)

    def test_listComprehensions_4(self):
        def listComprehensions_4(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4] if x != y]
            return aList[arg]

        for ix in range(-7, 7):
            self.equivalentEvaluationTest(listComprehensions_4, ix)

    def test_basicLists_1(self):
        def basicLists(x):
            aList = [x] + [x]
            return aList[0] + aList[1]

        self.equivalentEvaluationTest(basicLists, 1)

    def test_lists_1(self):
        x = [1,2,3,4]

        def f(ix):
            return x[ix]

        for ix in range(-len(x), len(x)):
            self.equivalentEvaluationTest(f, ix)

    def test_lists_2(self):
        class C_lists:
            def __init__(self, x):
                self.x = x
            def __eq__(self, other):
                return self.x == other.x

        xs = [1,2,3,C_lists(3)]

        def elt(ix):
            return xs[ix]

        for ix in range(-4,4):
            self.equivalentEvaluationTest(elt, ix)


    def test_listComprehensions_5(self):
        def listComprehensions_3(arg):
            aList = [(x, y) for x in [1,2,3] for y in [3,1,4]]
            return aList[arg]

        for ix in range(-9,9):
            self.equivalentEvaluationTest(listComprehensions_3, ix)

    def test_listComprehensions_6(self):
        def listComprehensions_1(arg):
            aList = [0,1,2,3]
            aList = [elt * 2 for elt in aList]
            return aList[arg]

        for ix in range(-4, 4):
            self.equivalentEvaluationTest(listComprehensions_1, ix)

    def test_nestedComprehensions_2(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.equivalentEvaluationTest(nestedComprehensions)


    def test_nestedLists_1(self):
        def nestedLists():
            x = [[0,1,2], [3,4,5], [7,8,9]]
            return x[0][0]

        self.equivalentEvaluationTest(nestedLists)


    def test_list_containing_itself(self):
        evilList = []
        evilList.append(evilList)

        try:
            self.equivalentEvaluationTest(lambda: len(evilList))
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertEqual(
                e.message,
                "don't know how to convert lists or tuples which reference themselves"
                )


    def test_nestedComprehensions_1(self):
        def nestedComprehensions():
            x = [[1,2], [3,4], [5,6]]
            res = [[row[ix] for row in x] for ix in [0,1]]

            return res[0][0]

        self.equivalentEvaluationTest(nestedComprehensions)


    def test_lists_plus_nonlists(self):
        def f():
            try:
                return [] + 10
            except TypeError:
                return None

        self.equivalentEvaluationTestThatHandlesExceptions(f)


    def test_access_list_comprehension_variable_fails(self):
        def f():
            try:
                result = [x for x in range(10)]
                return x
            except Exception:
                return "Exception"

        try:
            result = self.evaluateWithExecutor(f)
            self.assertTrue(False, result)
        except Exceptions.ComputationError as e:
            self.assertIsInstance(e.remoteException, Exceptions.InvalidPyforaOperation)


    def test_convertListOfTuple(self):
        x = [(3,4)]

        def returnX():
            return x

        self.equivalentEvaluationTest(returnX)


    def test_setitem_exception_is_meaningful(self):
        def f():
            l = [1,2,3]
            l[0] = 0

        try:
            self.evaluateWithExecutor(f)
            self.assertTrue(False)
        except Exceptions.PythonToForaConversionError as e:
            self.assertIsInstance(e.message, str)
            self.assertTrue(e.trace is not None)


    def test_holding_a_mappable_1(self):
        x = [len]
        def f():
            return x

        self.equivalentEvaluationTest(f)

    def test_holding_a_mappable_2(self):
        y = numpy.array(range(5))
        x = [y]
        def f():
            return x[0]

        self.equivalentEvaluationTest(f)
