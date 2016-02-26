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


import pyfora.pure_modules.pure_pandas as PurePandas


class AdditiveRegressionTree:
    def __init__(self, trees=None):
        if trees is None:
            trees = []

        self.trees = trees

    def numTrees(self):
        return len(self.trees)

    def getTree(self, ix):
        return self.trees[ix]

    def __add__(self, tree):
        return AdditiveRegressionTree(self.trees + [tree])

    def predict(self, x, nEstimators=None):
        if isinstance(x, PurePandas.PurePythonDataFrame):
            return x.apply(
                lambda row: self._predictionFunction(row, nEstimators),
                1
                )
        else:
            return self._predictionFunction(x, nEstimators)

    def _predictionFunction(self, row, nEstimators=None):
        if nEstimators is None:
            nEstimators = len(self.trees)

        return sum(tree.predict(row) for tree in self.trees[:nEstimators])

    def score(self, x, yTrue):
        sz = len(x)
        assert sz == len(yTrue)

        if isinstance(yTrue, PurePandas.PurePythonDataFrame):
            yTrue = yTrue.iloc[:, 0]

        yPredicted = self.predict(x)

        u = sum(
            (yTrue[ix] - yPredicted[ix]) ** 2.0 for ix in xrange(sz)
            )
        mean = sum(yTrue) / sz
        v = sum(
            (yTrue[ix] - mean) ** 2.0 for ix in xrange(sz)
            )

        return 1.0 - u / v
