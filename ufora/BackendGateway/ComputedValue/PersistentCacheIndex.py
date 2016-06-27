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

"""Maintains a background loop for submitting ComputedValue work to Cumulus"""

import ufora.BackendGateway.ComputedGraph.ComputedGraph as ComputedGraph
import ufora.native.Cumulus as CumulusNative
import ufora.native.FORA as ForaNative
import ufora.BackendGateway.ComputedValue.ComputedValueGateway as ComputedValueGateway
import ufora.BackendGateway.ComputedGraph.BackgroundUpdateQueue as BackgroundUpdateQueue

_no_tsunami_reload = True

getGateway = ComputedValueGateway.getGateway

class PersistentCacheIndex(ComputedGraph.Location):
    totalBytesInCache = ComputedGraph.Mutable(object, lambda: 0)
    totalObjectsInCache = ComputedGraph.Mutable(object, lambda: 0)
    totalComputationsInCache = ComputedGraph.Mutable(object, lambda: 0)
    totalReachableComputationsInCache = ComputedGraph.Mutable(object, lambda: 0)

    @ComputedGraph.ExposedProperty()
    def persistentCacheState(self):
        return {
            "totalBytesInCache": self.totalBytesInCache,
            "totalObjectsInCache": self.totalObjectsInCache,
            "totalComputationsInCache": self.totalComputationsInCache,
            "totalReachableComputationsInCache": self.totalReachableComputationsInCache
            }

    @ComputedGraph.ExposedFunction()
    def triggerGarbageCollectionImmediately(self, completePurge):
        ComputedValueGateway.getGateway().triggerPerstistentCacheGarbageCollection(
            True if completePurge else False
            )

    @ComputedGraph.ExposedFunction()
    def setMaxBytesInCache(self, *args):
        ComputedValueGateway.getGateway().getPersistentCacheIndex().setMaxBytesInCache(args[0])

    @ComputedGraph.ExposedProperty()
    def maxBytesInCache(self):
        if ComputedValueGateway.getGateway().getPersistentCacheIndex() is None:
            return 0

        return ComputedValueGateway.getGateway().getPersistentCacheIndex().getMaxBytesInCache()

    @ComputedGraph.Function
    def update(self):
        if ComputedValueGateway.getGateway().getPersistentCacheIndex() is None:
            return

        self.totalBytesInCache = ComputedValueGateway.getGateway().getPersistentCacheIndex().totalBytesInCache()
        self.totalObjectsInCache = ComputedValueGateway.getGateway().getPersistentCacheIndex().totalObjectsInCache()
        self.totalComputationsInCache = ComputedValueGateway.getGateway().getPersistentCacheIndex().totalComputationsInCache()
        self.totalReachableComputationsInCache = ComputedValueGateway.getGateway().getPersistentCacheIndex().totalReachableComputationsInCache()

