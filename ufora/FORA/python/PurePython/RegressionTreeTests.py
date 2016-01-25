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

import pyfora.algorithms.regressionTrees.Base as regressionTreeBase
import pyfora.algorithms.regressionTrees.RegressionTree as RegressionTree
import pyfora.typeConverters.PurePandas as PurePandas


import numpy


def generateData(mbOfData, nColumns):
    nRows = mbOfData * 1024 * 1024 / 8 / (nColumns + 1)
    nRows = int(nRows)
    
    dataVectors = [
        [float(rowIx % (colIx + 2)) for rowIx in xrange(nRows)] \
        for colIx in xrange(nColumns)]

    predictors = PurePandas.PurePythonDataFrame(dataVectors[:-1])
    responses = PurePandas.PurePythonDataFrame(dataVectors[-1:])

    return predictors, responses


class RegressionTreeTests(object):
    def test_SampleSummary_1(self):
        def f():
            s1 = regressionTreeBase.SampleSummary()
            s2 = regressionTreeBase.SampleSummary(1.0)
            s3 = regressionTreeBase.SampleSummary(2.0, 2.0, 2.0)

            s = (s3 + s2) - s1

            return (s.mean, s.stdev, s.variance, s.impurity())

        self.equivalentEvaluationTest(f)

    def test_SampleSummary_2(self):
        def f():
            s = regressionTreeBase.SampleSummary()
            return regressionTreeBase.SampleSummary.impurityImprovement(s, s)

        self.equivalentEvaluationTest(f)
    
    def test_MutableVector_1(self):
        sz = 5
        def f():
            m = regressionTreeBase._MutableVector(sz, 0)
            for ix in xrange(sz):
                m.setitem(ix, ix)
            return [val for val in m]

        self.assertEqual(
            self.evaluateWithExecutor(f),
            range(sz)
            )

    def test_MutableVector_2(self):
        sz = 4
        def f():
            m = regressionTreeBase._MutableVector(sz, 0)
            for ix in xrange(sz):
                m.augmentItem(ix, sz + ix)
            return [m[ix] for ix in range(len(m))]

        self.assertEqual(
            self.evaluateWithExecutor(f),
            range(sz, sz + sz)
            )

    def test_SampleSummaryHistogram_1(self):
        # verified against old fora implementation
        def f():
            hist = regressionTreeBase.SampleSummaryHistogram(
                0.0, 1.0, 5.0, False)

            s = regressionTreeBase.SampleSummary(3)
            hist.observe(0.1, s)
            hist.observe(1.2, regressionTreeBase.SampleSummary(2))
            hist.observe(2.8, regressionTreeBase.SampleSummary(1))
            hist.observe(3.9, regressionTreeBase.SampleSummary(2))
            hist.observe(4.4, regressionTreeBase.SampleSummary(3))


            return hist.bestSplitPointAndImpurityImprovement()

        bestSplitPoint, impurityImprovement = self.evaluateWithExecutor(f)

        self.assertEqual(bestSplitPoint, 0.2)
        self.assertTrue(numpy.isclose(impurityImprovement, 0.16))

    def test_RegressionTreeFitting_1(self):
        # verified against old fora implementation
        def f():
            x, y = generateData(0.01, 10)
            builder = RegressionTree.RegressionTreeBuilder(1)
            regressionTree = builder.fit(x,y)
            return regressionTree

        res = self.evaluateWithExecutor(f)
        
        self.assertEqual(len(res.rules), 3)

        self.assertTrue(
            numpy.isclose(res.rules[1].leafValue, 4.70833333333333)
            )
        self.assertTrue(
            numpy.isclose(res.rules[2].leafValue, 5.07042253521)
            )

    def test_RegressionTreeFitting_2(self):
        # verified against old fora implementation
        def f():
            x, y = generateData(1, 10)
            builder = RegressionTree.RegressionTreeBuilder(4)
            regressionTree = builder.fit(x,y)
            return regressionTree

        res = self.evaluateWithExecutor(f)
        
        self.assertEqual(len(res.rules), 31)

        rule_0 = res.rules[0]

        self.assertEqual(rule_0.rule.dimension, 8)
        self.assertTrue(numpy.isclose(rule_0.rule.splitPoint, 6.00000502164))
        self.assertTrue(
            numpy.isclose(rule_0.rule.impurityImprovement, 1.43744072627e-05)
            )
        self.assertEqual(rule_0.rule.numSamples, 11915)
        self.assertEqual(rule_0.jumpIfLess, 1)
        self.assertEqual(rule_0.jumpIfHigher, 16)
        self.assertTrue(numpy.isclose(rule_0.leafValue, 4.9992446496))
            
