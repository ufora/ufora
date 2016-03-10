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


import RegressionTree


class RegressionModel:
    """A class representing a gradient-boosted regression tree model fit to data.

    Note:
        These classes are not normally instantiated directly. Instead,
        they are typically returned by
        :class:`~pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.GradientBoostedRegressorBuilder`
        instances.
    """
    def __init__(
            self,
            additiveRegressionTree,
            X,
            XDimensions,
            yAsSeries,
            loss,
            regressionTreeBuilder,
            learningRate
            ):
        self.additiveRegressionTree = additiveRegressionTree
        self.X = X
        self.XDimensions = XDimensions
        self.yAsSeries = yAsSeries
        self.loss = loss
        self.regressionTreeBuilder = regressionTreeBuilder
        self.learningRate = learningRate

    def score(self, X, yTrue):
        """
        Return the coefficient of determination (R\ :sup:`2`\ ) of the prediction.

        The coefficient R\ :sup:`2` is defined as ``(1 - u / v)``, where ``u`` is
        the regression sum of squares ``((yTrue - yPredicted) ** 2).sum()`` and ``v``
        is the residual sum of squares ``((yTrue - yTrue.mean()) ** 2).sum()``.
        Best possible score is ``1.0``, lower values are worse.

        Args:
            X: the predictor DataFrame.
            yTrue: the (true) responses DataFrame.

        Returns:
            (float) the R\ :sup:`2` value.

        Example::

            from pyfora.algorithms import GradientBoostedRegressorBuilder

            builder = GradientBoostedRegressorBuilder(1, 1, 1.0)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            model = builder.fit(x, y)

            # compute the score of the fit model:
            model.score(x, y)

        """
        return self.additiveRegressionTree.score(X, yTrue)

    def predict(self, df, nEstimators=None):
        """Predict on the :class:`pandas.DataFrame` ``df``.

        Example::

            from pyfora.algorithms import GradientBoostedRegressorBuilder

            builder = GradientBoostedRegressorBuilder(1, 1, 1.0)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            model = builder.fit(x, y)

            # predict `x` using the model `model`:
            model.score(x, y)

        """
        return self.additiveRegressionTree.predict(df, nEstimators)

    def predictWithPreviousResult(self, previousPredictions, df):
        return previousPredictions + self.additiveRegressionTree.getTree(-1).predict(df)

    def pseudoResidualsAndPredictions(self, previousPredictions):
        if previousPredictions is None:
            predictions = self.predict(self.X)
        else:
            predictions = self.predictWithPreviousResult(previousPredictions, self.X)

        return self.loss.negativeGradient(self.yAsSeries, predictions), predictions

    @staticmethod
    def getInitialModel(X, yAsSeries, loss, learningRate, treeBuilderArgs):
        additiveRegressionTree = loss.initialModel(yAsSeries)
        XDimensions = range(X.shape[1])
        baseModelBuilder = RegressionTree.RegressionTreeBuilder(
            treeBuilderArgs.maxDepth,
            treeBuilderArgs.minSamplesSplit,
            treeBuilderArgs.numBuckets
            )

        if loss.needsOriginalYValues:
            X = X.pyfora_addColumn("__originalValues", yAsSeries)

        return RegressionModel(
            additiveRegressionTree,
            X,
            XDimensions,
            yAsSeries,
            loss,
            baseModelBuilder,
            learningRate
            )

    def boost(self, predictions, pseudoResiduals):
        localX = self.X
        targetDim = localX.shape[1]

        localX = localX.pyfora_addColumn("__pseudoResiduals", pseudoResiduals)

        if self.loss.needsPredictedValues:
            localX = localX.pyfora_addColumn("__predictedValues", predictions)

        nextRegressionTree = self.regressionTreeBuilder.fit_(
            localX,
            targetDim,
            None,
            self.XDimensions,
            self.loss.leafValueFun(self.learningRate),
            None)

        return RegressionModel(
            self.additiveRegressionTree + nextRegressionTree,
            self.X,
            self.XDimensions,
            self.yAsSeries,
            self.loss,
            self.regressionTreeBuilder,
            self.learningRate)

    def featureImportances(self):
        raise NotImplementedError()




