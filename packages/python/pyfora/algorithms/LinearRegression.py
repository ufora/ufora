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

"""
A pure-python implementation of linear regression
using the "normal equations": :math:`X^t X \beta = X^t y` by directly
inverting (or pseudo-inverting) the "covariance" matrix `X^t X`
"""

import numpy


def linearRegression(predictors, responses):
    """Compute the regression coefficients (with intercept) for a set of predictors
    against responses.

    Args:
        predictors (DataFrame): a :class:`pandas.DataFrame` with the predictor
            columns.
        responses (DataFrame): a :class:`pandas.DataFrame` whose first column is
            used as the regression's target.

    Returns:
        A :class:`numpy.array` with the regression coefficients. The last
            element in the array is the intercept.
    """
    XTX = _computeXTX(predictors)
    XTy = _computeXTy(predictors, responses.iloc[:, 0])
    XTXinv = numpy.linalg.pinv(XTX)

    return numpy.dot(XTy, XTXinv)[0]


_splitLimit = 1000000


def _loopSum(vec1):
    s = 0
    i = 0
    top = len(vec1)
    while i < top:
        s = s + vec1.iloc[i]
        i = i + 1

    return s


def _dotDontCheckLengths(vec1, vec2):
    s = 0
    i = 0
    top = len(vec1)
    while i < top:
        s = s + vec1.iloc[i] * vec2.iloc[i]
        i = i + 1

    return s


def _computeXTX(df, start=0, end=None, splitLimit=_splitLimit, fitIntercept=True):
    if end is None:
        end = df.shape[0]

    numRows = end - start
    if numRows <= splitLimit:
        numColumns = df.shape[1]

        if fitIntercept:
            numColumns = numColumns + 1

        def unsymmetrizedElementAt(row, col):
            """Fills out 'half' of the symmetric matrix XTX, filling in
            zeros above the main diagonal, to avoid computing dot products
            twice

            the full symmetric matrix XTX is filled out by reading the
            lower diagonal of this matrix.
            """
            if col < row:
                return 0.0

            if fitIntercept:
                if row == numColumns - 1 and col == numColumns - 1:
                    return float(numRows)

                if row == numColumns - 1:
                    return _loopSum(df.iloc[start:end, col])

                if  col == numColumns - 1:
                    return _loopSum(df.iloc[start:end, row])

            right = df.iloc[start:end, col]
            left = df.iloc[start:end, row]

            return _dotDontCheckLengths(right, left)

        unsymmetrizedValues = [
            [unsymmetrizedElementAt(row, col) for col in xrange(numColumns)] \
            for row in xrange(numColumns)
            ]

        symmetrizedValues = []
        for row in xrange(numColumns):
            for col in xrange(numColumns):
                if row <= col:
                    symmetrizedValues = symmetrizedValues + \
                        [unsymmetrizedValues[row][col]]
                else:
                    symmetrizedValues = symmetrizedValues + \
                        [unsymmetrizedValues[col][row]]

        tr = numpy.array(symmetrizedValues)

        return tr.reshape((numColumns, numColumns))

    mid = (start + end) / 2

    return _computeXTX(df, start, mid, splitLimit, fitIntercept) + \
        _computeXTX(df, mid, end, splitLimit, fitIntercept)


def _computeXTy(
        predictors,
        y,
        start=0,
        end=None,
        splitLimit=_splitLimit,
        fitIntercept=True):
    numPredictors = predictors.shape[1]

    if fitIntercept:
        numPredictors = numPredictors + 1

    if end is None:
        end = predictors.shape[0]

    if end - start <= splitLimit:
        def elementAt(columnIndex):
            if fitIntercept:
                if columnIndex == numPredictors - 1:
                    return _loopSum(y[start:end])

            columnVec = predictors.iloc[start:end, columnIndex]

            return _dotDontCheckLengths(columnVec, y[start:end])

        tr = numpy.array([elementAt(ix) for ix in xrange(numPredictors)])
        return tr.reshape((1, numPredictors))

    mid = (start + end) / 2

    return _computeXTy(predictors, y, start, mid, splitLimit, fitIntercept) + \
        _computeXTy(predictors, y, mid, end, splitLimit, fitIntercept)
