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

import unittest
import numpy
import ufora.native.Cumulus as CumulusNative
import ufora.FORA.python.FORA as FORA
import ufora.FORA.python.Evaluator.Evaluator as Evaluator
import ufora.FORA.python.Evaluator.LocalEvaluator as LocalEvaluator
import ufora.native.CallbackScheduler as CallbackScheduler

class TestVectorDataManager(unittest.TestCase):
    def setUp(self):
        self.callbackScheduler = CallbackScheduler.singletonForTesting()

        def createStorage(vdm):
            self.simpleOfflineCache = CumulusNative.SimpleOfflineCache(self.callbackScheduler, 1000000000)
            return self.simpleOfflineCache

        self.evaluator = LocalEvaluator.LocalEvaluator(
            createStorage,
            2000000,
            maxPageSizeInBytes = 100000
            )

        self.oldEvaluator = Evaluator.swapEvaluator(self.evaluator)

    def tearDown(self):
        self.evaluator.teardown()
        Evaluator.swapEvaluator(self.oldEvaluator)

    def test_vectors_clean_up(self):
        origPageCount = self.getVectorPageCount()

        self.assertEqual(
            FORA.eval(
                "[[ix for _ in sequence(12500)].paged for ix in sequence(500)].paged; 10"
                ),
            10
            )

        self.evaluator.getVDM().unloadAllPossible()
        self.assertEqual(
            self.getVectorPageCount(),
            origPageCount
            )

    def test_gc_working(self):
        origPageCount = self.getVectorPageCount()

        self.assertEqual(
            FORA.eval(
                "let res = 0;\n" +
                "for ix in sequence(10000) {\n" +
                "    res = res + [x for x in sequence(10000)][10]\n"
                "}; res"
                ),
            10 * 10000
            )

        self.evaluator.getVDM().unloadAllPossible()
        self.assertEqual(
            self.getVectorPageCount(),
            origPageCount
            )

    def test_extract_numpy_array(self):
        def numpytest(text, dtype, expr):
            array = FORA.extractImplValContainer(FORA.eval(text))

            nArray = self.evaluator.getVDM().extractVectorContentsAsNumpyArray(array, 0, array.getVectorSize())

            self.assertTrue(
                (nArray == expr.astype('int64')).all(),
                "Expected %s, got %s" % (expr.astype('int64'), nArray)
                )

        numpytest("Vector.range(1000)", 'int64', numpy.ones(1000).cumsum() - 1)
        numpytest("Vector.range(1000).paged", 'int64', numpy.ones(1000).cumsum() - 1)
        numpytest("Vector.range(500).paged + Vector.range((500,1000))", 'int64', numpy.ones(1000).cumsum() - 1)
        numpytest("(Vector.range(500).paged + Vector.range((500,1000)).paged)[1,,3]", 'int64', (numpy.ones(1000).cumsum() - 1)[1::3])
        numpytest("(Vector.range(500).paged + Vector.range((500,1000)).paged)[-1,,-1]", 'int64', (numpy.ones(1000).cumsum() - 1)[-1::-1])
        numpytest("Vector.range(1000.0)", 'double', numpy.ones(1000).cumsum() - 1)
        numpytest("Vector.range(1000.0).paged", 'double', numpy.ones(1000).cumsum() - 1)

    def test_extract_nonhomogenous_numpy_array_fails(self):
        array = FORA.extractImplValContainer(FORA.eval("[1,2,(3,4,5)]"))
        self.assertTrue(
            self.evaluator.getVDM().extractVectorContentsAsNumpyArray(array, 0, array.getVectorSize())
                is None
            )

    def test_stringify(self):
        array = FORA.extractImplValContainer(FORA.eval("[1,2,3.4]"))

        stringified = self.evaluator.getVDM().stringifyAndJoinVectorContents(
            array,
            ",",
            0,
            array.getVectorSize()
            )

        self.assertEqual(stringified, "1,2,3.4")

    def test_extract_vector_contents(self):
        def test(strForm, pyList):
            array = FORA.extractImplValContainer(FORA.eval(strForm))

            contents = self.evaluator.getVDM().extractVectorContentsAsPythonArray(
                array,
                0,
                array.getVectorSize()
                )

            contentsIndividually = [
                self.evaluator.getVDM().extractVectorItem(array, ix) for ix in
                    range(array.getVectorSize())
                ]

            vals = pyList

            self.assertEqual(contents, contentsIndividually)

            self.assertEqual(contents,
                [FORA.extractImplValContainer(FORA.eval(x, keepAsForaValue=True)) for x in vals]
                )

        #test("[1,2,(3,4,5)]", ["1","2","(3,4,5)"])
        #test("[1,2,3,4,5,6][1,-1]", ["2","3","4","5"])
        test("[1,2,3,4,5,6][-2,0,-1]", ["5","4","3","2"])

    def test_extract_vector_contents_using_slices(self):
        def test(strForm, pyList):
            array = FORA.extractImplValContainer(FORA.eval(strForm))

            contents = []

            for low,high in array.getVectorPageSliceRanges(self.evaluator.getVDM()):
                contents += self.evaluator.getVDM().extractVectorContentsAsPythonArray(
                    array,
                    low,
                    high
                    )

            contentsIndividually = [
                self.evaluator.getVDM().extractVectorItem(array, ix) for ix in
                    range(array.getVectorSize())
                ]

            vals = pyList

            self.assertEqual(contents, contentsIndividually)

            self.assertEqual(contents,
                [FORA.extractImplValContainer(FORA.eval(x, keepAsForaValue=True)) for x in vals]
                )

        test("[1,2,3,4].paged + [5,6]", ["1","2","3","4","5","6"])
        test("[1,2,3,4].paged[1,2] + [5,6]", ["2","5","6"])

    def getVectorPageCount(self):
        return self.evaluator.getVDM().getVectorPageCount()

