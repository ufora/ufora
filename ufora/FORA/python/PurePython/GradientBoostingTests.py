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


from pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder \
    import GradientBoostedRegressorBuilder
from pyfora.algorithms.regressionTrees.GradientBoostedClassifierBuilder \
    import GradientBoostedClassifierBuilder
import pyfora.typeConverters.PurePandas as PurePandas
import pyfora.algorithms.regressionTrees.RegressionTree as RegressionTree


import numpy
import pandas


def generateRegressionData(mbOfData, nColumns):
    nRows = mbOfData * 1024 * 1024 / 8 / (nColumns + 1)
    nRows = int(nRows)
    
    dataVectors = [
        [float(rowIx % (colIx + 2)) for rowIx in xrange(nRows)] \
        for colIx in xrange(nColumns)]

    predictors = PurePandas.PurePythonDataFrame(dataVectors[:-1])
    responses = PurePandas.PurePythonDataFrame(dataVectors[-1:])

    return predictors, responses


def generateClassificationData(mbOfData, nColumns):
    nRows = mbOfData * 1024 * 1024 / 8 / (nColumns + 1)
    nRows = int(nRows)
    
    dataVectors = [
        [float(rowIx % (colIx + 2)) for rowIx in xrange(nRows)] \
        for colIx in xrange(nColumns)]

    predictors = PurePandas.PurePythonDataFrame(dataVectors[:-1])

    responses = [float(int(elt) % 2) for elt in dataVectors[-1]]
    responses = PurePandas.PurePythonDataFrame([responses])

    return predictors, responses


class GradientBoostingTests(object):
    def test_gradient_boosting_classification_1(self):
        # verified against old fora implementation

        def f():
            x, y = generateClassificationData(0.1, 10)
            
            builder = GradientBoostedClassifierBuilder(1, 1, 1.0)
            fit = builder.fit(x, y)
            return fit.additiveRegressionTree.trees
            

        trees = self.evaluateWithExecutor(f)

        self.assertEqual(len(trees), 2)

        self.assertEqual(len(trees[0].rules), 1)
        node_0_0 = trees[0].rules[0]
        self.assertIsInstance(node_0_0, RegressionTree.RegressionLeafRule)
        self.assertTrue(numpy.isclose(node_0_0.leafValue, 0.0))
        
        self.assertEqual(len(trees[1].rules), 3)
        node_1_0 = trees[1].rules[0]
        self.assertEqual(node_1_0.jumpIfLess, 1)
        self.assertEqual(node_1_0.jumpIfHigher, 2)
        self.assertTrue(
            numpy.isclose(node_1_0.leafValue, -0.09151973131822)
            )
        self.assertEqual(node_1_0.rule.dimension, 8)        
        self.assertTrue(
            numpy.isclose(node_1_0.rule.splitPoint, 8.00024176403741),
            (node_1_0.rule.splitPoint, 3.00115009354123)
            )
        self.assertTrue(
            numpy.isclose(
                node_1_0.rule.impurityImprovement,
                2.80266701735421e-05
                )
            )

        node_1_1 = trees[1].rules[1]
        self.assertIsInstance(
            node_1_1,
            RegressionTree.RegressionLeafRule
            )
        self.assertTrue(
            numpy.isclose(node_1_1.leafValue, -0.0932835820895522)
            )
         
        node_1_2 = trees[1].rules[2]
        self.assertIsInstance(
            node_1_2,
            RegressionTree.RegressionLeafRule
            )
        self.assertTrue(
            numpy.isclose(node_1_2.leafValue, -0.0756302521008403)
            )

    def test_gradient_boosting_classification_2(self):
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})

        def f():
            model = GradientBoostedClassifierBuilder(1, 1, 1.0).fit(x, y)
            return model.score(x, y)

        self.assertEqual(
            self.evaluateWithExecutor(f),
            1.0
            )

    def test_gradient_boosting_classification_3(self):
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})

        def f():
            model = GradientBoostedClassifierBuilder(1, 1, 1.0).fit(x, y)
            return model.predict(x)

        self.assertEqual(
            [elt for elt in self.evaluateWithExecutor(f)],
            [elt for elt in y.iloc[:,0]]
            )

    def test_gradient_boosting_classification_4(self):
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})

        def f():
            model = GradientBoostedClassifierBuilder(1, 1, 1.0).fit(x, y)
            return model.deviance(x, y)

        self.assertTrue(
            numpy.isclose(self.evaluateWithExecutor(f), 0.126928011043)
            )
 
    def test_gradient_boosting_regression_1(self):
        # verified against old fora implementation

        def f():
            x, y = generateRegressionData(0.1, 10)
            
            builder = GradientBoostedRegressorBuilder(1, 1, 1.0)
            fit = builder.fit(x, y)
            return fit.additiveRegressionTree.trees
            

        trees = self.evaluateWithExecutor(f)

        self.assertEqual(len(trees), 2)

        self.assertEqual(len(trees[0].rules), 1)
        node_0_0 = trees[0].rules[0]
        self.assertIsInstance(node_0_0, RegressionTree.RegressionLeafRule)
        self.assertTrue(numpy.isclose(node_0_0.leafValue, 4.98992443325))
        
        self.assertEqual(len(trees[1].rules), 3)
        node_1_0 = trees[1].rules[0]
        self.assertEqual(node_1_0.jumpIfLess, 1)
        self.assertEqual(node_1_0.jumpIfHigher, 2)
        self.assertTrue(
            numpy.isclose(node_1_0.leafValue, -1.99858787976183e-16)
            )
        self.assertEqual(node_1_0.rule.dimension, 8)

        self.assertTrue(
            numpy.isclose(node_1_0.rule.splitPoint, 3.00115009354123),
            (node_1_0.rule.splitPoint, 3.00115009354123)
            )
        self.assertTrue(
            numpy.isclose(
                node_1_0.rule.impurityImprovement,
                0.00093093285723711
                )
            )
        self.assertEqual(node_1_0.rule.numSamples, 1191)

        node_1_1 = trees[1].rules[1]
        self.assertIsInstance(
            node_1_1,
            RegressionTree.RegressionLeafRule
            )
        self.assertTrue(
            numpy.isclose(node_1_1.leafValue, 0.0373292355137323)
            )
         
        node_1_2 = trees[1].rules[2]
        self.assertIsInstance(
            node_1_2,
            RegressionTree.RegressionLeafRule
            )
        self.assertTrue(
            numpy.isclose(node_1_2.leafValue, -0.0249384388516114)
            )

    def test_gradient_boosting_regression_2(self):
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})

        def f():
            model = GradientBoostedRegressorBuilder(1, 1, 1.0).fit(x, y)
            return model.score(x, y)

        self.assertEqual(self.evaluateWithExecutor(f), 1.0)

    def test_gradient_boosting_regression_3(self):
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})

        def f():
            model = GradientBoostedRegressorBuilder(1, 1, 1.0).fit(x, y)
            return model.predict(x)

        self.assertEqual(
            [elt for elt in self.evaluateWithExecutor(f)],
            [elt for elt in y.iloc[:,0]]
            )
