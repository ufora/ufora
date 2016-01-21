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


class _IterativeFitter:
    def __init__(self, model, predictions):
        self.model = model
        self.predictions = predictions

    def next(self):
        pseudoResiduals, newPredictions = \
            self.model.pseudoResidualsAndPredictions(self.predictions)
        newModel = self.model.boost(newPredictions, pseudoResiduals)

        return _IterativeFitter(newModel, newPredictions)

    def predictionsAndPseudoresiduals(self):
        return self.model.pseudoResidualsAndPredictions(
            self.predictions
            )

    def nextGivenPredictions(self, pseudoResiduals, newPredictions):
        newModel = self.model.boost(newPredictions, pseudoResiduals)

        return _IterativeFitter(newModel, newPredictions)


class GradientBoostedRegressorBuilder:
    def __init__(self, maxDepth=3, nBoosts=100, learningRate=1.0, 
                  minSamplesSplit=2, numBuckets=10000, loss="l2"):
        if loss == 'l2':
            loss = losses.L2_loss()
        elif loss == 'lad':
            loss = losses.Absoluteloss()
        else:
            assert False, "invalid `loss` argument: " + str(loss)

        treeBuilderArgs = treeBase.TreeBuilderArgs(
            minSamplesSplit, maxDepth, treeBase.SampleSummary, numBuckets
            )

        self.loss = loss
        self.nBoostingIterations = nBoosts
        self.learningRate = learningRate
        self.treeBuilderArgs = treeBuilderArgs

    def iterativeFitter(self, X, y):
        yAsSeries = y.iloc[:,0]
        model = self._getInitialModel(X, yAsSeries)

        return _IterativeFitter(model, None)

    def _getInitialModel(self, X, yAsSeries):
        return RegressionModel.RegressionModel.getInitialModel(
            X, yAsSeries, self.loss, self.learningRate, self.treeBuilderArgs
            )

    def fit(self, X, y):
        iterativeFitter = self.iterativeFitter(X, y)
        boostingIx = 0
        while boostingIx < self.nBoostingIterations:
            iterativeFitter = iterativeFitter.next()
            boostingIx = boostingIx + 1

        return iterativeFitter.model
        
