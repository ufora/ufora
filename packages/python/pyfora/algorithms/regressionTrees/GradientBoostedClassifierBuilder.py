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


import pyfora.algorithms.regressionTrees.Base as treeBase
from pyfora.algorithms.regressionTrees.BinaryClassificationModel \
    import BinaryClassificationModel


class IterativeFitter:
    """A sort of iterator class which is capable of fitting subsequent 
    boosting models.

    Typically not instantiated directy: instead these classes are 
    returned from `GradientBoostedClassifierBuilder.iterativeFitter`.

    Args/Attributes:
        model: the current regression model.
        predictions: the current predictions of the regression model 
            (with respect to the training set implicit in `model`).
    """
    def __init__(self, model, previousRegressionValues):
        self.model = model
        self.previousRegressionValues = previousRegressionValues

    def next(self):
        pseudoResiduals, regressionValues = \
            self.model.pseudoResidualsAndRegressionValues(
                self.previousRegressionValues
                )

        newModel = self.model.boost(pseudoResiduals)

        return IterativeFitter(
            newModel,
            regressionValues
            )

    def pseudoResidualsAndRegressionValues(self):
        return self.model.pseudoResidualsAndRegressionValues(
            self.previousRegressionValues
            )


class GradientBoostedClassifierBuilder:
    """A class which builds (or "fits") uses gradient boosted (regression) 
    trees to form classification models. These parameters are 

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
                 minSamplesSplit=2, numBuckets=10000):
        self.nBoostingIterations = nBoosts
        self.learningRate = learningRate
        self.treeBuilderArgs = treeBase.TreeBuilderArgs(
            minSamplesSplit,
            maxDepth,
            numBuckets
            )

    def iterativeFitter(self, X, y):
        """
        Create an :class:`~IterativeFitter` instance which can iteratively 
        fit boosting models.

        Args:
            X (:class:`~pandas.DataFrame`): giving the predictors.
            y (:class:`~pandas.DataFrame`): giving the responses.

        Examples::

            builder = pyfora.algorithms.regressionTrees\
                .GradientBoostedClassifierBuilder\
                .GradientBoostedClassifierBuilder(1, 1, 1.0)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            fitter = builder.iterativeFitter(x, y)

            numBoosts = 5
            for ix in xrange(numBoosts):
                fitter = fitter.next()
        """
        yAsSeries = y.iloc[:, 0]
        model = self._getInitialModel(X, yAsSeries)

        return IterativeFitter(model, None)

    def _getInitialModel(self, X, yAsSeries):
        classes = yAsSeries.unique()
        nClasses = len(classes)

        assert nClasses > 1, "in a classification model, the number of classes" + \
            " must be greater than one."

        if nClasses == 2:
            return BinaryClassificationModel.getInitialModel(
                X, yAsSeries, classes, self.learningRate, self.treeBuilderArgs
                )

        raise NotImplementedError("not implementing nClasses > 2 case yet")

    def fit(self, X, y):
        """Use a `GradientBoostedRegressorBuilder` `self` to fit predictors
        `X` to responses `y`.

        Args:
            X (:class:`pandas.DataFrame`): giving the predictors.
            y (:class:`pandas.DataFrame`): giving the responses.

        Examples::

            builder = pyfora.algorithms.regressionTrees.GradientBoostedClassifierBuilder.GradientBoostedClassifierBuilder(1, 1, 1.0)
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
