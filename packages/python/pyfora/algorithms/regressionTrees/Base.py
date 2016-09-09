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


class SampleSummary:
    """An additive class to track statistics of samplesets (mean, std-dev, count)"""
    def __init__(self, xSum=None, weight=None, xxSum=None):
        if xSum is None:
            self.weight = 0.0
            self.xSum = 0.0
            self.xxSum = 0.0
        elif weight is None:
            self.weight = 1.0
            self.xSum = xSum
            self.xxSum = xSum * xSum
        else:
            self.weight = weight
            self.xSum = xSum
            self.xxSum = xxSum

    @property
    def mean(self):
        return self.xSum / self.weight

    @property
    def stdev(self):
        return self.variance ** 0.5

    @property
    def variance(self):
        mean = self.mean
        return (self.xxSum / self.weight - mean * mean)

    def impurity(self):
        return self.variance

    def __str__(self):
        return "SampleSummary(weight: " + str(self.weight) + \
            ", xSum: " + str(self.xSum) + \
            ", xxSum: " + str(self.xxSum) + ")"

    def __add__(self, other):
        return SampleSummary(
            self.xSum + other.xSum,
            self.weight + other.weight,
            self.xxSum + other.xxSum
            )

    def __sub__(self, other):
        return SampleSummary(
            self.xSum - other.xSum,
            self.weight - other.weight,
            self.xxSum - other.xxSum
            )
        
    @staticmethod
    def impurityImprovement(sampleSummary1, sampleSummary2):
        # computes the change in impurity by splitting the union of 
        # the points described by sampleSummary1 and sampleSummary2 
        # into those pieces

        if sampleSummary1.weight == 0 or sampleSummary2.weight == 0:
            return -float("inf")

        return (sampleSummary1 + sampleSummary2).variance - \
            (sampleSummary1.variance * sampleSummary1.weight + \
            sampleSummary2.variance * sampleSummary2.weight) / \
            (sampleSummary1.weight + sampleSummary2.weight)
            

class SampleSummaryHistogram:
    """A class which maintains xValue-bucketed `SampleSummary`s of y-values"""
    def __init__(self, x0, x1, samplesOrCount, isSamples=True):
        if isSamples:
            self.count = len(samplesOrCount)
            self.x0 = x0
            self.x1 = x1
            self.samples = samplesOrCount
        else:
            self.count = samplesOrCount
            self.x0 = x0
            self.x1 = x1
            self.samples = _MutableVector(self.count, SampleSummary())

    def observe(self, xValue, sample):
        try:
            bucket = (xValue - self.x0) / (self.x1 - self.x0) * self.count
        except ZeroDivisionError:
            bucket = (xValue - self.x0) * float("inf") * self.count
        bucket = max(bucket, 0)
        bucket = min(bucket, self.count - 1)

        self.samples.augmentItem(bucket, sample)

    def bestSplitPointAndImpurityImprovement(self):
        above = SampleSummary()
        for sample in self.samples:
            above = above + sample
        below = self.samples[0]
        above = above - below
        
        bestIx = 0
        bestImpurityImprovement = SampleSummary.impurityImprovement(above, below)

        curIx = 1
        while curIx + 1 < len(self.samples):
            above = above - self.samples[curIx]
            below = below + self.samples[curIx]

            impurityImprovement = SampleSummary.impurityImprovement(
                above, below)

            if impurityImprovement > bestImpurityImprovement:
                bestImpurityImprovement = impurityImprovement
                bestIx = curIx

            curIx = curIx + 1

        return (self.x0 + ((bestIx + 1) * (self.x1 - self.x0) / self.count),
                bestImpurityImprovement)        

    def freeze(self):
        return SampleSummaryHistogram(
            self.x0,
            self.x1,
            [s for s in self.samples]
            )

    def __add__(self, other):
        assert self.x0 == other.x0 and self.x1 == other.x1

        newSamples = []
        for ix in xrange(len(self.samples)):
            newSamples = newSamples + [self.samples[ix] + other.samples[ix]]

        return SampleSummaryHistogram(
            self.x0,
            self.x1,
            newSamples,
            True
            )


class _MutableVector:
    def __init__(self, count, defaultValue):
        self.samples = __inline_fora(
            """fun(@unnamed_args:(count, defaultValue), *args) {
                   MutableVector(`TypeJOV(defaultValue))
                       .create(count.@m, defaultValue)
                   }"""
            )(count, defaultValue)

    def setitem(self, ix, val):
        __inline_fora(
            """fun(@unnamed_args:(samples, ix, val), *args) {
                   samples[ix.@m] = val
                   }"""
            )(self.samples, ix, val)

    def __getitem__(self, ix):
       return  __inline_fora(
            """fun(@unnamed_args:(samples, ix), *args) {
                   samples[ix.@m]
                   }"""
            )(self.samples, ix)

    def augmentItem(self, ix, val):
        __inline_fora(
            """fun(@unnamed_args:(samples, ix, val), *args) {
                   let foraIx = ix.@m;
                   samples[foraIx] = samples[foraIx] + val
                   }"""
            )(self.samples, ix, val)

    def __len__(self):
        return __inline_fora(
            """fun(@unnamed_args:(samples), *args) {
                   PyInt(size(samples))
                   }"""
            )(self.samples)

    def __iter__(self):
        for ix in xrange(len(self)):
            yield self[ix]

class SplitRule:
    def __init__(self, rule, jumpIfLess, jumpIfHigher, leafValue):
        self.rule = rule
        self.jumpIfLess = jumpIfLess
        self.jumpIfHigher = jumpIfHigher
        self.leafValue = leafValue

    def __str__(self):
        return "SplitRule(rule: " + str(self.rule) + \
            ", less->" + str(self.jumpIfLess) + \
            ", higher->" + str(self.jumpIfHigher) + \
            ", leafValue->" + str(self.leafValue) + ")"


class Rule:
    def __init__(self, dimension, splitPoint, impurityImprovement, numSamples):
        self.dimension = dimension
        self.splitPoint = splitPoint

        # these next to members are with respect to training set which produced
        # this rule, if any
        self.impurityImprovement = impurityImprovement
        self.numSamples = numSamples

    def isLess(self, row):
        return row[self.dimension] < self.splitPoint

    # not a great name ...
    # using our rule, split the dataset into two subsets, 
    # and return sample summaries of each piece"""
    def summaryPair(self, xVec, yVec, impurityMeasure=SampleSummary):
        def f(ix):
            if xVec[ix] < self.splitPoint:
                return ImpurityPair(
                    impurityMeasure(yVec[ix]),
                    impurityMeasure()
                    )
            else:
                return impurityMeasure(
                    impurityMeasure(),
                    impurityMeasure(yVec[ix])
                    )

        return sum((f(ix) for ix in xrange(len(xVec))), ImpurityPair())

    def splitDataframe(self, df, activeIndices):
        xColumn = df.iloc[:, self.dimension]
        
        leftIndices = [ix for ix in activeIndices if xColumn[ix] < self.splitPoint]
        rightIndices = [ix for ix in activeIndices if xColumn[ix] >= self.splitPoint]

        return leftIndices, rightIndices

    def __str__(self):
        return "Rule(dim: " + str(self.dimension) + \
            ", splitPoint: " + str(self.splitPoint) + \
            ", impurityImprovement: " + str(self.impurityImprovement) + \
            ", numSamples: " + str(self.numSamples) + ")"


class ImpurityPair:
    def __init__(self, leftImpurity=None, rightImpurity=None):
        if leftImpurity is None:
            leftImpurity = 0.0
        if rightImpurity is None:
            rightImpurity = 0.0

        self.leftImpurity = leftImpurity
        self.rightImpurity = rightImpurity

    def __add__(self, other):
        return ImpurityPair(
            self.leftImpurity + other.leftImpurity,
            self.rightImpurity + other.rightImpurity
            )


class TreeBuilderArgs:
    def __init__(self, minSamplesSplit, maxDepth, numBuckets):
        self.minSamplesSplit = minSamplesSplit
        self.maxDepth = maxDepth
        self.numBuckets = numBuckets


