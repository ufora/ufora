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


import pyfora.typeConverters.PurePandas as PurePandas
import pyfora.algorithms.regressionTrees.Base as treeBase


class RegressionTree:
    def __init__(self, rules, numDimensions=None, columnNames=None):
        self.rules = rules
        self.numDimensions = numDimensions
        self.columnNames = columnNames

    def featureImportances(self):
        raise NotImplementedError()

    def rawFeatureImportances(self):
        raise NotImplementedError()

    def predict(self, x, depth=None):
        if isinstance(x, PurePandas.PurePythonDataFrame):
            return x.apply(
                lambda row: self._predictionFunction(row, depth),
                1
                )
        else:
            return self._predictionFunction(x, depth)

    def _predictionFunction(self, row, depth=None):
        if depth is None:
            depth = 1000000

        ix = 0
        currentDepth = 0
        while True:
            rule = self.rules[ix]
            if isinstance(rule, treeBase.SplitRule):
                if currentDepth == depth:
                    return rule.leafValue
                
                if rule.rule.isLess(row):
                    ix = ix + rule.jumpIfLess
                else:
                    ix = ix + rule.jumpIfHigher
            else: # rule must be a leaf value
                return rule.predictionValue

    def score(self, x, y):
        raise NotImplementedError()


class RegressionLeafRule:
    def __init__(self, leafValue):
        self.leafValue = leafValue

    def __str__(self):
        return "RegressionLeafRule(leafValue: " + \
            str(self.leafValue) + ")"

    def predict(self, _):
        return self.leafValue


class RegressionTreeBuilder:
    def __init__(
            self,
            maxDepth,
            impurityMeasure=treeBase.SampleSummary,
            minSamplesSplit=2,
            minSplitThresh=1000000,
            numBuckets=10000
            ):
        self.maxDepth = maxDepth
        self.impurityMeasure = impurityMeasure
        self.minSamplesSplit = minSamplesSplit
        self.minSplitThresh = minSplitThresh
        self.numBuckets = numBuckets

    @staticmethod
    def samplesummary(xVec):
        return sum(
            (treeBase.SampleSummary(xVec[ix]) for ix in xrange(len(xVec))),
            treeBase.SampleSummary()
            )

    def bestRule(self, df, yDim, xDimensions, activeIndices):
        bestRuleByDimension = [
            self.bestRuleForXDimension(df, yDim, ix, activeIndices) \
            for ix in xDimensions
            ]

        bestRuleIx = argmax(
            [rule.impurityImprovement for rule in bestRuleByDimension]
            )

        return bestRuleByDimension[bestRuleIx]

    @staticmethod
    def sampleSummary(xVec):
        return sum(
            (treeBase.SampleSummary(xVec[ix]) for ix in xrange(len(xVec))),
            treeBase.SampleSummary()
            )

    def bestRuleForXDimension(self, df, yDim, xDim, activeIndices):
        xColumn = _OnDemandSelectedVector(df.iloc[:, xDim], activeIndices)
        yColumn = _OnDemandSelectedVector(df.iloc[:, yDim], activeIndices)

        xColumnSampleSummary = RegressionTreeBuilder.sampleSummary(xColumn)

        bucketedSampleSummaries = self.computeBucketedSampleSummaries(
            xColumn, yColumn,
            xColumnSampleSummary.mean - xColumnSampleSummary.stdev * 3.0,
            xColumnSampleSummary.mean + xColumnSampleSummary.stdev * 3.0,
            self.numBuckets
            )

        splitPoint, impurityImprovement = \
            bucketedSampleSummaries.bestSplitPointAndImpurityImprovement()

        return treeBase.Rule(
            xDim,
            splitPoint,
            impurityImprovement,
            len(activeIndices)
            )

    def computeBucketedSampleSummaries(
            self, xCol, yCol, x0, x1, count, low=0, high=None):
        if high is None:
            high = len(xCol)

        if high - low < self.minSplitThresh:
            hist = treeBase.SampleSummaryHistogram(x0, x1, count, False)

            for ix in xrange(low, high):
                hist.observe(xCol[ix], treeBase.SampleSummary(yCol[ix]))

            return hist.freeze()

        mid = (low + high) / 2

        return self.computeBucketedSampleSummaries(
            xCol, yCol, x0, x1, count, low, mid) + \
            self.computeBucketedSampleSummaries(
                xCol, yCol, x0, x1, count, mid, high)

    def fit(self, x, y):
        if isinstance(y, PurePandas.PurePythonDataFrame):
            assert y.shape[1] == 1
            y = y.iloc[:, 0]

        return self.fit_(
            x.pyfora_addColumn("__target", y),
            x.shape[1],
            self.maxDepth,
            range(x.shape[1])
            )

    def fit_(self, df, yDim, maxDepth=None, xDimensions=None, leafValueFun=None, activeIndices=None):
        if maxDepth is None:
            maxDepth = self.maxDepth

        if xDimensions is None:
            xDimensions = [ix for ix in xrange(df.shape[1]) if ix != yDim]

        if leafValueFun is None:
            leafValueFun = RegressionTreeBuilder.defaultLeafValueFun(yDim)

        if activeIndices is None:
            activeIndices = range(len(df))

        if len(activeIndices) < self.minSamplesSplit or maxDepth == 0:
            return RegressionTree(
                [RegressionLeafRule(
                    leafValueFun(df, activeIndices)
                    )],
                len(xDimensions)
                )

        bestRule = self.bestRule(df, yDim, xDimensions, activeIndices)

        leftIndices, rightIndices = bestRule.splitDataframe(df, activeIndices)

        if len(leftIndices) == 0 or len(rightIndices) == 0:
            return RegressionTree(
                [RegressionLeafRule(
                    leafValueFun(df, activeIndices)
                    )],
                len(xDimensions)
                )

        nextDepth = maxDepth - 1
        treeLeft = self.fit_(
            df, yDim, nextDepth,
            xDimensions,
            leafValueFun,
            leftIndices
            )
        treeRight = self.fit_(
            df, yDim, nextDepth,
            xDimensions,
            leafValueFun,
            rightIndices
            )

        treeLeft = treeLeft.rules
        treeRight = treeRight.rules

        leafValue = (len(leftIndices) * treeLeft[0].leafValue + \
                     len(rightIndices) * treeRight[0].leafValue) / \
            (len(leftIndices) + len(rightIndices))

        return RegressionTree(
            [treeBase.SplitRule(
                bestRule,
                1,
                1 + len(treeLeft),
                leafValue
                )] + treeLeft + treeRight,
            len(xDimensions)
            )            
    
    @staticmethod
    def defaultLeafValueFun(yDim):
        def f(values, activeIndices):
            selectedValues = _OnDemandSelectedVector(values.iloc[:, yDim], activeIndices)
            
            sz = len(selectedValues)

            if sz == 0:
                return float("nan")

            return sum(selectedValues) / float(sz)

        return f

    @staticmethod
    def buildTree(x, y, minSamplesSplit, maxDepth, impurityMeasure):
        return RegressionTreeBuilder(
            maxDepth,
            impurityMeasure,
            minSamplesSplit,
            ).fit(x, y)            


class _OnDemandSelectedVector:
    def __init__(self, vectorToSelectFrom, selectingIndices):
        self.vectorToSelectFrom = vectorToSelectFrom
        self.selectingIndices = selectingIndices

    def __getitem__(self, ix):
        return self.vectorToSelectFrom[self.selectingIndices[ix]]

    def __len__(self):
        return len(self.selectingIndices)

    def __iter__(self):
        for ix in xrange(len(self)):
            yield self[ix]


def argmax(vec):
    curMax = vec[0]
    curMaxIx = 0

    for ix in xrange(len(vec)):
        val = vec[ix]
        if vec[ix] > curMax:
            curMax = val
            curMaxIx = ix

    return curMaxIx
