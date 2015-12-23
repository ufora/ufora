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


import math
import numpy
import pyfora.typeConverters.PurePandas as PurePandas


def logit_complement(x):
    return 1.0 / (1.0 + math.exp(x))


class BinaryLogisticRegressionModel:
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
            X: feature vectors
            y: target labels, corresponding to the vectors in `X`.

        Returns:
            score: (float) the mean accuracy of `self.predict(X)` 
                with respect to `y`.
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
        Predict the class labels of `X`.

        Args:
            X: (DataFrame, or numpy array) a set of feature vectors

        Returns:
            a numpy array containing the predicted class labels.
        """
        probabilities = self.predict_probability(X)

        def classForProbability(probability):
            if probability <= 0.5:
                return self.classOneLabel
            return self.classZeroLabel

        return numpy.array([
            classForProbability(p) for p in probabilities
            ])

    def predict_probability(self, X):
        """
        Estimate the conditional class-one probability for the features in 
        `X`.

        Args:
            X: (DataFrame, or numpy array) a set of feature vectors

        Returns:
            a numpy array containing the predicted probabilities.
        """
        if isinstance(X, PurePandas.PurePythonDataFrame):
            X = X.as_matrix()

        res = numpy.dot(X, self.coefficients)

        if self.intercept is not None:
            res = res + self.intercept * self.interceptScale

        return numpy.array([
            logit_complement(val) for val in res
            ])
            
