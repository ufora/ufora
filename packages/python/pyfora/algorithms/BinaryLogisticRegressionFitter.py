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

import pyfora.algorithms.util


class BinaryLogisticRegressionFitter:
    def __init__(
            self,
            regulizer,
            hasIntercept=True,
            strict=True,
            interceptScale=1,
            tol=1e-4,
            maxIter=1e5,
            chunkSize=5000000):
        assert tol > 0
        assert maxIter > 0
        assert chunkSize > 0

        self.regulizer = regulizer
        self.hasIntercept = hasIntercept
        self.strict = strict
        self.interceptScale = interceptScale
        self.tol = tol
        self.maxIter = maxIter
        self.chunkSize = chunkSize

    def fit(self, X, y, classZeroLabel=None, classOneLabel=None, classes=None):
        assert X.shape[0] == y.shape[0]
        assert y.shape[1] == 1

        if classes is None:
            # we need to be careful here:
            # sorted is going to copy the 
            # maybe we can avoid the copy, but at the very least
            # we should build implement  __pyfora_generator__  on Series
            classes = y.iloc[:,0].unique()

        nClasses = len(classes)

        if self.strict and nClasses != 2:
            assert False

        return classes
            
