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
import ufora.BackendGateway.control.Control as Control
import ufora.distributed.SharedState.ComputedGraph.SharedStateSynchronizer as SharedStateSynchronizer
import ufora.BackendGateway.ComputedGraph.BackgroundUpdateQueue as BackgroundUpdateQueue
import ufora.BackendGateway.SubscribableWebObjects.Exceptions as Exceptions


class SubscriptionKeys(ComputedGraph.Location):
    subscriptionKeys = ComputedGraph.Mutable(object)

    def keys(self):
        if self.subscriptionKeys is None:
            return []
        return self.subscriptionKeys

class Subscriptions(object):
    """Manage a set of "Subscriptions" into the ComputedGraph.

    We use the control framework. This is a hack for expediency.
    """
    def __init__(self, computedGraph, computedValueGateway, sharedStateSynchronizer):
        self.controlRoot = Control.root(
            Control.overlayGenerated(
                lambda: SubscriptionKeys().keys,
                self.controlForKey_
                ),
            computedGraph,
            self
            )
        self.computedGraph = computedGraph
        self.computedValueGateway = computedValueGateway
        self.sharedStateSynchronizer = sharedStateSynchronizer

        self.subscriptionGetters = {}
        self.subscriptionValues = {}
        self.changedSubscriptions = set()

    def isDisconnectedFromSharedState(self):
        return self.sharedStateSynchronizer.isSharedStateDisconnected()

    def subscriptionCount(self):
        return len(self.subscriptionGetters)

    def updateComputedGraph_(self):
        self.sharedStateSynchronizer.update()

        BackgroundUpdateQueue.moveNextFrameToCurFrame()
        BackgroundUpdateQueue.pullAll()

        self.computedGraph.flushOrphans()
        self.computedGraph.flush()

        self.controlRoot.pruneDirtyChildren()
        self.controlRoot.update()

        #self.controlRoot.display()

        self.sharedStateSynchronizer.commitPendingWrites()

    def updateAndReturnChangedSubscriptionIds(self):
        self.updateComputedGraph_()

        result = self.changedSubscriptions
        self.changedSubscriptions = set()

        return sorted(list(result))

    def getValueAndDropSubscription(self, subscriptionId):
        result = self.subscriptionValues[subscriptionId]
        self.removeSubscription(subscriptionId)
        return result

    def removeSubscription(self, subscriptionId):
        del self.subscriptionGetters[subscriptionId]
        del self.subscriptionValues[subscriptionId]

    def addSubscription(self, subscriptionId, resultGetter):
        self.subscriptionGetters[subscriptionId] = resultGetter

        SubscriptionKeys().subscriptionKeys = list(self.subscriptionGetters.keys())

        changedSubscriptions = self.updateAndReturnChangedSubscriptionIds()

        return self.subscriptionValues[subscriptionId], changedSubscriptions

    def recomputeSubscription_(self, subscriptionId):
        if subscriptionId not in self.subscriptionGetters:
            return

        try:
            newValue = self.subscriptionGetters[subscriptionId]()
        except Exception as e:
            e = Exceptions.wrapException(e)
            newValue = e

        if subscriptionId not in self.subscriptionValues:
            self.subscriptionValues[subscriptionId] = newValue
            return

        existingValue = self.subscriptionValues[subscriptionId]

        if existingValue != newValue:
            self.changedSubscriptions.add(subscriptionId)
            self.subscriptionValues[subscriptionId] = newValue


    def controlForKey_(self, subscriptionId):
        def gen(parent):
            self.recomputeSubscription_(subscriptionId)
            return Control.empty()

        return Control.generated(gen)

