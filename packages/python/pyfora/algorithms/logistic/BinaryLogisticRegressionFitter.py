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

from pyfora.algorithms.logistic.FullRankMajorizationSolver import \
    FullRankMajorizationSolver
from pyfora.algorithms.logistic.TrustRegionConjugateGradientSolver import \
    TrustRegionConjugateGradientSolver
from pyfora.algorithms.logistic.BinaryLogisticRegressionModel import \
    BinaryLogisticRegressionModel
import pyfora.pure_modules.pure_pandas as PurePandas


class BinaryLogisticRegressionFitter(object):
    """
    BinaryLogisticRegressionFitter

    A logistic regression "fitter" ithat holds fitting parameters used to fit logit models.

    Args:
        C (float): Inverse of regularization strength; must be a positive float.
        hasIntercept (bool): If True, include an intercept (aka bias) term in
            the fitted models.
        method (string): one of 'newton-cg' (default) or 'majorization'
        interceptScale (float): When ``hasIntercept`` is True, feature vectors
            become ``[x, interceptScale]``, i.e. we add a "synthetic" feature
            with constant value ``interceptScale`` to all of the feature vectors.
            This synthetic feature is subject to regularization as all other
            features. To lessen the effect of regularization, users should
            increase this value.
        tol (float): Tolerance for stopping criteria. Fitting stops when
            the l2-norm of the parameters to update do not change more than ``tol``.
        maxIter (int): A hard limit on the number of update cycles allowed.
    """
    def __init__(
            self,
            C,
            hasIntercept=True,
            method='newton-cg',
            interceptScale=1.0,
            tol=1e-4,
            maxIter=1e5,
            splitLimit=1000000):
        assert tol > 0, "tol must be > 0"
        assert maxIter > 0, "maxIter must be > 0"
        assert C > 0, "C must be > 0"

        self.regularizer = float(C)
        self.hasIntercept = hasIntercept
        self.method = method
        self.interceptScale = interceptScale
        self.tol = tol
        self.maxIter = maxIter
        self.splitLimit = splitLimit

    def _addScaleColumn(self, df):
        return df.pyfora_addColumn(
            "intercept", [self.interceptScale for _ in xrange(len(df))])

    def fit(self, X, y):
        """
         fit a (regularized) logit model to the predictors ``X`` and responses ``y``.

        Args:
            X: a dataframe of feature vectors.
            y: a dataframe (with one column) which contains the "target" values,
                corresponding to the feature vectors in ``X``.

        Returns:
            A :class:`~pyfora.algorithms.BinaryLogisticRegressionModel.BinaryLogisticRegressionModel`
            which represents the fit model.

        Example::

            # fit a logit model without intercept using regularizer 1.0

            from pyfora.algorithms import BinaryLogisticRegressionFitter

            fitter = BinaryLogisticRegressionFitter(1.0, False)
            x = pandas.DataFrame({'x0': [-1,0,1], 'x1': [0,1,1]})
            y = pandas.DataFrame({'y': [0,1,1]})

            model = fitter.fit(x, y)

        """
        assert len(X) == len(y), "len(X) doesn't match len(y)"

        if isinstance(y, PurePandas.PurePythonDataFrame):
            assert y.shape[1] == 1, "for dataframe y, need y.shape[1] == 1"
            y = y.iloc[:,0]

        # we need to be careful here:
        # sorted is going to copy the
        # maybe we can avoid the copy, but at the very least
        # we should build implement  __pyfora_generator__  on Series
        classes = y.unique()

        assert len(classes) == 2, "need len(classes) == 2"

        classZeroLabel = classes[0]
        classOneLabel = classes[1]

        # TODO: we don't need to hold onto an entire column of ones,
        # but it simplifies the code for now.
        # this logic should move into the subclasses of Solver.Solver
        if self.hasIntercept:
            X = self._addScaleColumn(X)

        if self.method == 'newton-cg':
            returnValue = TrustRegionConjugateGradientSolver(
                X, y,
                classZeroLabel=classZeroLabel,
                C=self.regularizer,
                eps=self.tol,
                maxIters=self.maxIter,
                splitLimit=self.splitLimit
                ).solve()
        elif self.method == 'majorization':
            returnValue = FullRankMajorizationSolver(
                X, y,
                classZeroLabel=classZeroLabel,
                regularizer=1.0 / len(X) / self.regularizer,
                tol=self.tol,
                maxIters=self.maxIter,
                splitLimit=self.splitLimit
                ).solve()
        else:
            raise Exception("bad method argument passed in: " + self.method)

        intercept = None
        if self.hasIntercept:
            intercept = returnValue.weights[-1]
            weights = returnValue.weights[:-1]
        else:
            weights = returnValue.weights

        return BinaryLogisticRegressionModel(
            weights,
            classZeroLabel,
            classOneLabel,
            intercept,
            self.interceptScale,
            returnValue.iterations)

