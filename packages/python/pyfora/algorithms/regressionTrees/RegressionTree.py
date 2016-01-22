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
import Base as treeBase


class RegressionTree:
    """A class representing a regression tree.

    A regression tree is represented, essentially, as a list of "rules",
    which are either `pyfora.algorithms.regressionTrees.Base.SplitRule`s, giving
    "split" nodes, which divide the domain by a hyperplane, or `RegressionLeafRule`s,
    which just hold a prediction value.
    """
    def __init__(self, rules, numDimensions=None, columnNames=None):
        self.rules = rules
        self.numDimensions = numDimensions
        self.columnNames = columnNames

    def featureImportances(self):
        raise NotImplementedError()

    def rawFeatureImportances(self):
        raise NotImplementedError()

    def predict(self, x, depth=None):
        """
        Using the regression tree `self`, use it to predict the responses
        corresponding to dataframe `x`.
        """
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
                return rule.leafValue

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
    """Fits regression trees to data using specified tree parameters.
    
    Args:
        maxDepth (int): The maximum depth of a fit tree
        minSamplesSplit (int): The minimum number of samples required to split  a node
        numBuckets (int): The number of buckets used in the estimation of optimal
            column splits.
        minSplitThresh (int): an "internal" argument, not generally of interest to
            casual users, giving the splitting rule in `computeBucketedSampleSummaries`

    Examples::
        
        from pyfora.algorithms import RegressionTreeBuilder

        builder = RegressionTreeBuilder(2)
        x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
        y = pandas.DataFrame({'y': [0,1,1]})
        regressionTree = builder.fit(x, y)
    
    """
    def __init__(
            self,
            maxDepth,
            minSamplesSplit=2,
            numBuckets=10000,
            minSplitThresh=1000000
            ):
        self.maxDepth = maxDepth
        self.impurityMeasure = treeBase.SampleSummary
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
        xColumn = OnDemandSelectedVector(df.iloc[:, xDim], activeIndices)
        yColumn = OnDemandSelectedVector(df.iloc[:, yDim], activeIndices)

        xColumnSampleSummary = RegressionTreeBuilder.sampleSummary(xColumn)

        bucketedSampleSummaries = self.computeBucketedSampleSummaries(
            xColumn,
            yColumn,
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
        """Using a :class:`~pyfora.algorithms.regressionTrees.RegressionTree.RegressionTreeBuilder`, 
        fit a regression tree to predictors `x` and responses `y`.

        Args:
            x (:class:`pandas.DataFrame`): of the predictors.
            y (:class:`pandas.DataFrame`): giving the responses.

        Returns: a :class:`~pyfora.algorithms.regressionTrees.RegressionTree.RegressionTree`
        instance.
      
        Examples::
        
            builder = pyfora.algorithms.regressionTrees.RegressionTree.RegressionTreeBuilder(2)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})
            regressionTree = builder.fit(x, y)
        
        """
        if isinstance(y, PurePandas.PurePythonDataFrame):
            assert y.shape[1] == 1
            y = y.iloc[:, 0]

        return self.fit_(
            x.pyfora_addColumn("__target", y),
            x.shape[1],
            self.maxDepth,
            range(x.shape[1])
            )

    def fit_(self,
             df,
             yDim,
             maxDepth=None,
             xDimensions=None,
             leafValueFun=None,
             activeIndices=None):
        if maxDepth is None:
            maxDepth = self.maxDepth

        if xDimensions is None:
            xDimensions = [ix for ix in xrange(df.shape[1]) if ix != yDim]

        if leafValueFun is None:
            leafValueFun = RegressionTreeBuilder.defaultLeafValueFun(yDim)

        if activeIndices is None:
            activeIndices = range(len(df))

        if len(activeIndices) < self.minSamplesSplit or maxDepth == 0:
            leafValue = leafValueFun(df, activeIndices)
            return RegressionTree(
                [RegressionLeafRule(
                    leafValue
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
        def tr(values, activeIndices):
            selectedValues = OnDemandSelectedVector(values.iloc[:, yDim], activeIndices)
            
            sz = len(selectedValues)

            if sz == 0:
                return float("nan")

            return sum(selectedValues) / float(sz)

        return tr

    @staticmethod
    def buildTree(x, y, minSamplesSplit, maxDepth):
        """Fit a regression tree to predictors `x` and responses `y` using
        parameters `minSamplesSplit` and `maxDepth`.

        Args:
            x (:class:`pandas.DataFrame`): of the predictors.
            y (:class:`pandas.DataFrame`): giving the responses.
            maxDepth: The maximum depth of a fit tree
            minSamplesSplit: The minimum number of samples required to split  a node
        """
        return RegressionTreeBuilder(
            maxDepth,
            treeBase.SampleSummary,
            minSamplesSplit,
            ).fit(x, y)            


class OnDemandSelectedVector:
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
