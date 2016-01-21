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


from pyfora.algorithms.regressionTrees.AdditiveRegressionTree \
    import AdditiveRegressionTree
from pyfora.algorithms.regressionTrees.RegressionTree \
    import RegressionTree, OnDemandSelectedVector, RegressionLeafRule
import pyfora.typeConverters.PureNumpy as PureNumpy
import pyfora.typeConverters.PurePandas as PurePandas


class L2_loss:
    def __init__(self):
        self.needsTargetColumn = True
        self.needsPredictedValues = False
        self.needsOriginalYValues = False

    def initialModel(self, y):
        return AdditiveRegressionTree([
            RegressionTree(
                [RegressionLeafRule(
                    PureNumpy.Mean()(y)
                    )]
                )
            ])

    def negativeGradient(self, y, predicted_y):
        assert len(y) == len(predicted_y)

        def valFun(ix):
            return y[ix] - predicted_y[ix]

        return PurePandas.PurePythonSeries(
            [valFun(ix) for ix in xrange(len(y))]
            )

    def leafValueFun(self, learningRate):
        def f(leafValuesDf, activeIndices):
            return learningRate * PureNumpy.Mean()(
                OnDemandSelectedVector(
                    leafValuesDf.iloc[:, -1],
                    activeIndices
                    )
                )
        return f

class Absoluteloss:
    def __init__(self):
        self.needsTargetColumn = False
        self.needsPredictedValues = True
        self.needsOriginalYValues = True

    def initialModel(self, y):
        predictionValue = PureNumpy.Median()(y)
        return AdditiveRegressionTree([
            RegressionTree(
                [RegressionLeafRule(
                    predictionValue
                    )]
                )
            ])

    def negativeGradient(self, y, predicted_y):
        assert len(y) == len(predicted_y)

        def valFun(ix):
            tr = y[ix] - predicted_y[ix]
            return 2.0 * (tr > 0.0) - 1.0

        return PurePandas.PurePythonSeries(
            [valFun(ix) for ix in xrange(len(y))]
            )

    def leafValueFun(self, learningRate, yDim):
        def f(leafValuesDf, activeIndices):
            originalYInRegion = OnDemandSelectedVector(
                leafValuesDf.iloc[:, yDim],
                activeIndices
                )
            predictedYInRegion = OnDemandSelectedVector(
                leafValuesDf.iloc[:, -1],
                activeIndices
                )
                
            return learningRate * PureNumpy.Median()(
                [originalYInRegion[ix] - predictedYInRegion[ix] for \
                 ix in xrange(len(originalYInRegion))]
                )
                
        return f


