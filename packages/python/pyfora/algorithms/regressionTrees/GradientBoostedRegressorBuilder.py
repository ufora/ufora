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


import pyfora.algorithms.regressionTrees.losses as losses
import pyfora.algorithms.regressionTrees.Base as treeBase
import pyfora.algorithms.regressionTrees.RegressionModel as RegressionModel


class IterativeFitter:
    """A sort of iterator class which is capable of fitting subsequent
    boosting models.

    Typically not instantiated directy: instead these classes are
    returned from `GradientBoostedRegressorBuilder.iterativeFitter`.

    Args/Attributes:
        model: the current regression model.
        predictions: the current predictions of the regression model
            (with respect to the training set implicit in `model`).
    """
    def __init__(self, model, predictions):
        self.model = model
        self.predictions = predictions

    def next(self):
        """
        Fit one boosting stage to `self`, returning a new 
        :class:`~pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.Iterativefitter`
        object, holding the next
        regression model and predictions.
        """
        pseudoResiduals, newPredictions = \
            self.model.pseudoResidualsAndPredictions(self.predictions)

        newModel = self.model.boost(newPredictions, pseudoResiduals)

        return IterativeFitter(newModel, newPredictions)

    def predictionsAndPseudoresiduals(self):
        return self.model.pseudoResidualsAndPredictions(
            self.predictions
            )


class GradientBoostedRegressorBuilder:
    """A class which builds (or "fits") gradient-boosted regression trees to
    data with specified parameters. These parameters are

    Args:
        maxDepth (int): The max depth allowed of each constituent regression tree.
        nBoosts (int): The number of "boosting iterations" used.
        learningRate (float): The learning rate of the model, used for regularization.
            Each successive tree from boosting stages are added with multiplier
            `learningRate`.
        minSamplesSplit (int): The minimum number of samples required to split a
            regression tree node.
        numBuckets (int): The number of buckets used in the estimation of optimal
           column splits for building regression trees.
        loss: the loss used when forming gradients. Defaults to "l2", for
            least-squares loss. The only other allowed value currently is
            "lad", for "least absolute deviation" (aka l1-loss).
    """
    def __init__(self, maxDepth=3, nBoosts=100, learningRate=1.0, 
                  minSamplesSplit=2, numBuckets=10000, loss="l2"):
        if loss == 'l2':
            loss = losses.L2_loss()
        elif loss == 'lad':
            loss = losses.Absoluteloss()
        else:
            assert False, "invalid `loss` argument: " + str(loss)

        treeBuilderArgs = treeBase.TreeBuilderArgs(
            minSamplesSplit, maxDepth, numBuckets
            )

        self.loss = loss
        self.nBoostingIterations = nBoosts
        self.learningRate = learningRate
        self.treeBuilderArgs = treeBuilderArgs

    def iterativeFitter(self, X, y):
        """
        Create an :class:`~pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.Iterativefitter`
        instance which can iteratively fit boosting models.

        Args:
            X (:class:`pandas.DataFrame`): giving the predictors.
            y (:class:`pandas.DataFrame`) giving the responses.

        Examples::

            builder = pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.GradientBoostedRegressorBuilder(1, 1, 1.0)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            fitter = builder.iterativeFitter(x, y)

            numBoosts = 5
            for ix in xrange(numBoosts):
                fitter = fitter.next()
            fitter.score(x, y)
        """
        yAsSeries = y.iloc[:, 0]
        model = self._getInitialModel(X, yAsSeries)

        return IterativeFitter(model, None)

    def _getInitialModel(self, X, yAsSeries):
        return RegressionModel.RegressionModel.getInitialModel(
            X, yAsSeries, self.loss, self.learningRate, self.treeBuilderArgs
            )

    def fit(self, X, y):
        """Use the :class:`~pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.GradientBoostedRegressorBuilder`
        `self` to fit predictors `X` to responses `y`.

        Args:
            X (:class:`pandas.DataFrame`): giving the predictors.
            y (:class:`pandas.DataFrame`): giving the responses.

        Returns:
            A :class:`~pyfora.algorithms.regressionTrees.RegressionModel.RegressionModel`
            instance.

        Examples::

            builder = pyfora.algorithms.regressionTrees.GradientBoostedRegressorBuilder.GradientBoostedRegressorBuilder(1, 1, 1.0)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            model = builder.fit(x, y)

        """
        iterativeFitter = self.iterativeFitter(X, y)
        boostingIx = 0
        while boostingIx < self.nBoostingIterations:
            iterativeFitter = iterativeFitter.next()
            boostingIx = boostingIx + 1

        return iterativeFitter.model
        
