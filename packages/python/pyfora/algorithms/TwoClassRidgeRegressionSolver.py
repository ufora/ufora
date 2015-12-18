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


import numpy
import math


def _addScaleColumn(df, scale):
    return df.pyfora_addColumn("intercept", [scale for _ in xrange(len(df))])


class TwoClassRidgeRegressionSolver:
    def __init__(
            self, X, y,
            regularizer, tol, maxIter, classes,
            classZeroLabel=None, splitLimit=1000000,
            hasIntercept=True, interceptScale=1):
        if classZeroLabel is None:
            classZeroLabel = classes[0]
        else:
            assert classZeroLabel in classes

        # TODO: we don't need to hold onto an entire column of one, but it simplifies the code for now
        if hasIntercept:
            X = _addScaleColumn(X, interceptScale)

        fSum = TwoClassRidgeRegressionSolver.computeFSum(X, y.iloc[:,0], classZeroLabel)

        self.X = X
        self.regularizer = float(regularizer)
        self.tol = tol
        self.maxIter = maxIter
        self.classZeroLabel = classZeroLabel
        self.fSum = fSum
        self.nFeatures = X.shape[1]
        self.nSamples = X.shape[0]
        self.splitLimit = splitLimit

    @staticmethod
    def computeFSum(X, y, classZeroLabel):
        fSums = []
        for colIx in xrange(X.shape[1]):
            X_column = X.iloc[:,colIx]

            def f(rowIx):
                if y[rowIx] == classZeroLabel:
                    return 0.0

                return float(X_column[rowIx])

            fSums = fSums + [sum([f(rowIx) for rowIx in xrange(X.shape[0])])]

        return numpy.array(fSums)
        
    def computeCoefficients(self):
        oldTheta = numpy.zeros(self.nFeatures)
        newTheta = self.updateTheta(oldTheta)

        iters = 1
        while sum((newTheta - oldTheta) ** 2) > self.tol * self.tol and \
                  iters < self.maxIter:
            oldTheta = newTheta
            newTheta = self.updateTheta(oldTheta)
            iters = iters + 1

        return newTheta, iters

    def updateTheta(self, theta):
        thetaDotX = _dot(self.X, theta)
        sigma = self.computeSigma(thetaDotX)
        muSum = self.computeMuSum(thetaDotX)

        A = sigma + _diagonal(sigma.shape[0], self.X.shape[0] * self.regularizer)
        b = muSum - self.fSum + theta * (self.regularizer * self.X.shape[0])

        return theta - numpy.linalg.solve(A, b)

    def computeSigma(self, thetaDotX, start=0, end=None, depth=0):
        # we have a few choices here: 
        # 1) We can precompute all of the outer products of the rows
        #    of X. This will require nCols * storage of X to hold,
        #    which may be prohibitive. Assuming this is held in a 
        #    single flattened vector, it would require a "strided"
        #    access patten to compute the weighted sums of these 
        #    outer products.
        # 2) We can compute the outer products as needed in a manner
        #    similar to the way we compute the X^t X matrix for linear 
        #    regression, this time usin "weighted dot products" on the 
        #    columns of X. This is the choice we're using for now.

        if end is None:
            end = len(thetaDotX)

        if depth >=3 or (end - start) < self.splitLimit:
            numColumns = self.X.shape[1]

            def unsymmetrizedElementAt(row, col):
                if col < row:
                    return 0.0

                right = self.X.iloc[start:end, col]
                left = self.X.iloc[start:end, row]
                weights = thetaDotX[start:end]

                return _weightedDotProduct(right, left, weights)

            unsymmetrizedValues = [
                [unsymmetrizedElementAt(row, col) for col in xrange(numColumns)] \
                for row in xrange(numColumns)
                ]

            symmetrizedValues = []
            for row in xrange(numColumns):
                for col in xrange(numColumns):
                    if row <= col:
                        elt = unsymmetrizedValues[row][col]
                    else:
                        elt = unsymmetrizedValues[col][row]
                    symmetrizedValues = symmetrizedValues + [elt]

            tr = numpy.array(symmetrizedValues)
            return tr.reshape((numColumns, numColumns))

        mid = (start + end) / 2
        return self.computeSigma(thetaDotX, start, mid, depth + 1) + \
            self.computeSigma(thetaDotX, mid, end, depth + 1)

    def computeMuSum(self, thetaDotX):
        # we could compute this as needed, instead of making a new vector
        # each time, but we need this multiple for each column
        rowWiseScalarMultipliers = [
            1.0 / (1.0 + math.exp(-val)) for val in thetaDotX
            ]

        def computeWeightedColumnSum(columnIx):
            column = self.X.iloc[:,columnIx]
            return sum([
                rowWiseScalarMultipliers[ix] * column[ix] \
                for ix in xrange(self.X.shape[0])
                ])

        return numpy.array([
            computeWeightedColumnSum(columnIx) for columnIx in xrange(self.X.shape[1])
            ])


def _dot(X, theta):
    tr = numpy.array(X.iloc[:,0].values)
    tr = tr * theta[0]
    for ix in xrange(1, len(theta)):
        tr = tr + numpy.array(X.iloc[:,ix].values) * theta[ix]
    return tr
    

def _weightedDotProduct(x1, x2, x3):
    res = 0
    ix = 0
    top = len(x1)
    while ix < top:
        res = res + x1[ix] * x2[ix] * _weightFun(x3[ix])
        ix = ix + 1

    return res


def _weightFun(x):
    exp_x = math.exp(x)

    if abs(x) < 1.0e-5:
        # taylor expand (exp(x) - 1) / (2x) near the origin
        return (0.5 - 0.25 * x) / (exp_x + 1.0)

    return (exp_x - 1.0) / (exp_x + 1.0) / (2.0 * x)


def _diagonal(n, value):
    value = float(value)

    def eltAtIx(ix):
        if ix % n == ix / n:
            return value
        else:
            return 0.0

    vals = [eltAtIx(ix) for ix in xrange(n * n)]

    tr = numpy.array(vals)
    tr = tr.reshape((n, n))

    return tr
        
