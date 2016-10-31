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
import scipy.special
import pyfora.pure_modules.pure_pandas as PurePandas


class BinaryLogisticRegressionModel(object):
    """
    Represents a fit logit model.

    Attributes:
        coefficients (numpy.array): The regressions coefficients.
        intercept (float): The fitted model's intercept

    Note:
        This class is not intended to be constructed directly. Instances of it are
        returned by :func:`~pyfora.algorithms.BinaryLogisticRegressionFitter.fit`.
    """
    def __init__(
            self,
            coefficients,
            classZeroLabel,
            classOneLabel,
            intercept,
            interceptScale,
            iters):
        self.coefficients = coefficients
        self.classZeroLabel = classZeroLabel
        self.classOneLabel = classOneLabel
        self.intercept = intercept
        self.interceptScale = interceptScale
        self.iters = iters

    def score(self, X, y):
        """
        Returns the mean accuracy on the given test data and labels.

        Args:
            X (DataFrame): Feature vectors
            y (DataFrame): Target labels, corresponding to the vectors in ``X``.

        Returns:
            float: The mean accuracy of
            :func:`~pyfora.algorithms.logistic.BinaryLogisticRegressionModel.BinaryLogisticRegressionModel.predict`
            with respect to ``y``.
        """
        assert len(X) == len(y), "arguments must have the same length"

        if isinstance(y, (PurePandas.PurePythonSeries,
                          PurePandas.PurePythonDataFrame)):
            y = y.as_matrix()
            y = y.reshape((len(y),))

        predictions = self.predict(X)

        def valAtIx(ix):
            if y[ix] == predictions[ix]:
                return 1.0
            return 0.0

        return sum(valAtIx(ix) for ix in xrange(len(predictions))) / len(y)

    def predict(self, X):
        """
        Predict the class labels of ``X``.

        Args:
            X (DataFrame, or numpy.array): a set of feature vectors

        Returns:
            numpy.array: array containing the predicted class labels.
        """
        probabilities = self.predict_probability(X)

        def classForProbability(probability):
            if probability > 0.5:
                return self.classOneLabel
            return self.classZeroLabel

        return numpy.array([
            classForProbability(p) for p in probabilities
            ])

    def predict_probability(self, X):
        """
        Estimate the conditional class-zero probability for the features in ``X``.

        Args:
            X (DataFrame, or numpy.array): a set of feature vectors

        Returns:
            numpy.array: array containing the predicted probabilities.
        """
        res = X.dot(self.coefficients)

        if self.intercept is not None:
            res = res + self.intercept * self.interceptScale

        return numpy.array([
            scipy.special.expit(-val) for val in res
            ])

