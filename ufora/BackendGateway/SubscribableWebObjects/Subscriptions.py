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

import collections


class Subscriptions(object):
    """Manage a set of "Subscriptions" into the ComputedGraph.

    We use the control framework. This is a hack for expediency.
    """
    def __init__(self):
        self.cancellation_funcs = {}
        self.subscriptionValues = {}
        self.subscriptions_by_object = collections.defaultdict(set)
        self.changedSubscriptions = set()


    def subscriptionCount(self):
        return len(self.cancellation_funcs)


    def addSubscription(self, subscription_id, observable, field_name):
        def observer(observable_id, field, new_value, old_value):
            assert observable_id == observable.id
            assert field == field_name
            if new_value != old_value:
                self.subscriptionValues[subscription_id] = new_value
                self.changedSubscriptions.add(subscription_id)

        def unobserve():
            observable.unobserve(field_name, observer)

        observable.observe(field_name, observer)
        self.cancellation_funcs[subscription_id] = (observable.id, unobserve)
        self.subscriptions_by_object[observable.id].add(subscription_id)


    def updateAndReturnChangedSubscriptionIds(self):
        result = self.changedSubscriptions
        self.changedSubscriptions = set()
        return sorted(list(result))


    def getValueAndDropSubscription(self, subscriptionId):
        result = self.subscriptionValues[subscriptionId]
        self.removeSubscription(subscriptionId)
        return result


    def removeSubscription(self, subscriptionId):
        object_id, unobserve = self.cancellation_funcs[subscriptionId]
        unobserve()
        del self.cancellation_funcs[subscriptionId]
        del self.subscriptionValues[subscriptionId]
        self.subscriptions_by_object[object_id].discard(subscriptionId)


    def removeAllSubscriptionsForObject(self, objectId):
        object_subscriptions = list(self.subscriptions_by_object[objectId])
        for subscriptionId in object_subscriptions:
            self.removeSubscription(subscriptionId)
