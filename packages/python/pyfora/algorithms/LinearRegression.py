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
`LinearRegression`: a pure-python implementation of linear regression
using the "normal equations": `X^t X \beta = X^t y` by directly
inverting (or pseudo-inverting) the "covariance" matrix `X^t X`
"""

import numpy


def linearRegression(predictors, responses):
    """
    Compute the regression coefficients (with intercept) of `predictors` 
    against `responses`. Returns the result in a numpy array. The last
    value is the intercept.

    Arguments:
        `predictors`: a pandas dataframe.
        `responses`: a pandas dataframe. only the first column is read out
    """
    XTX = _computeXTX(predictors)
    XTy = _computeXTy(predictors, responses.iloc[:,0])
    XTXinv = numpy.linalg.pinv(XTX)

    return numpy.dot(XTy, XTXinv)


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

        def elementAt(row, col):
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

        tr = numpy.array([
            elementAt(row, col) for row in xrange(numColumns) for col in xrange(numColumns)
            ])

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
        fitIntercept=True
        ):
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
