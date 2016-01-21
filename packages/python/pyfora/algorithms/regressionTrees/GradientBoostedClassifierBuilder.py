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


class _IterativeFitter:
    def __init__(self, model, previousRegressionValues):
        self.model = model
        self.previousRegressionValues = previousRegressionValues

    def next(self):
        pseudoResiduals, regressionValues = \
            self.model.pseudoResidualsAndRegressionValues(
                self.previousRegressionValues
                )

        newModel = self.model.boost(pseudoResiduals)

        return _IterativeFitter(
            newModel,
            regressionValues
            )

    def pseudoResidualsAndRegressionValues(self):
        return self.model.pseudoResidualsAndRegressionValues(
            self.previousRegressionValues
            )


class GradientBoostedClassifierBuilder:
    def __init__(self, maxDepth=3, nBoosts=100, learningRate=1.0,
                 minSamplesSplit=2, numBuckets=10000):
        self.nBoostingIterations = nBoosts
        self.learningRate = learningRate
        self.treeBuilderArgs = treeBase.TreeBuilderArgs(
            minSamplesSplit,
            maxDepth,
            treeBase.SampleSummary,
            numBuckets
            )

    def iterativeFitter(self, X, y):
        yAsSeries = y.iloc[:, 0]
        model = self._getInitialModel(X, yAsSeries)

        return _IterativeFitter(model, None)

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
        iterativeFitter = self.iterativeFitter(X, y)
        boostingIx = 0
        while boostingIx < self.nBoostingIterations:
            iterativeFitter = iterativeFitter.next()
            boostingIx = boostingIx + 1

        return iterativeFitter.model
