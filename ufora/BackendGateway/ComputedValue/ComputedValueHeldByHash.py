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

import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.BackendGateway.ComputedValue.ComputedValue as ComputedValue
import ufora.native.FORA as ForaNative


class ComputedValueHeldByHash(ComputedValue.ComputedValue):
    args = None
    hash = object

    valueIVC_ = ComputedGraph.Mutable(object)

    def valueIVC(self):
        if self.valueIVC_ is None:
            return ForaNative.ImplValContainer()
        return self.valueIVC_

    isException = object
    isFinished = True
    workerCount = 0
    cacheloadCount = 0
    computationStatistics = None

allImplvals_ = set()

def create(ivc, isException = False):
    cv = ComputedValueHeldByHash(hash = str(ivc.hash), isException = isException)
    cv.valueIVC_ = ivc
    allImplvals_.add(cv)

    return cv

def clearAll():
    for cv in allImplvals_:
        cv.valueIVC = None
    allImplvals_.clear()



