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

from ufora.BackendGateway.SubscribableWebObjects.SubscribableObject \
    import SubscribableObject, ExposedFunction, ExposedProperty, observable


class ViewOfEntireCumulusSystem(SubscribableObject):
    def __init__(self, id, cumulus_gateway, cache_loader, _):
        super(ViewOfEntireCumulusSystem, self).__init__(id, cumulus_gateway, cache_loader)

        self.viewOfSystem_ = None
        self.recentGlobalUserFacingLogMessages_ = None
        self.totalMessageCountsEver_ = None

        self.cumulus_gateway.onJsonViewOfSystemChanged = self.onJsonViewOfSystemChanged


    @ExposedProperty
    def mostRecentMessages(self):
        return self.recentGlobalUserFacingLogMessages_


    @mostRecentMessages.setter
    @observable
    def mostRecentMessages(self, value):
        self.recentGlobalUserFacingLogMessages_ = value


    @ExposedProperty
    def totalMessagesEver(self):
        return self.totalMessageCountsEver_


    @totalMessagesEver.setter
    @observable
    def totalMessagesEver(self, value):
        self.totalMessageCountsEver_ = value


    @ExposedFunction
    def clearMostRecentMessages(self, _):
        self.recentGlobalUserFacingLogMessages_ = ()


    @ExposedFunction
    def clearAndReturnMostRecentMessages(self, _):
        messages = self.recentGlobalUserFacingLogMessages_
        self.recentGlobalUserFacingLogMessages_ = ()
        return messages


    @ExposedProperty
    def viewOfCumulusSystem(self):
        return self.viewOfSystem_


    @viewOfCumulusSystem.setter
    @observable
    def viewOfCumulusSystem(self, value):
        self.viewOfSystem_ = value


    @ExposedFunction
    def pushNewGlobalUserFacingLogMessage(self, msg):
        self.totalMessageCountsEver_ = self.totalMessageCountsEver_ + 1
        self.recentGlobalUserFacingLogMessages_ = (
            self.recentGlobalUserFacingLogMessages_ + (
                {
                    "timestamp": msg.timestamp,
                    "message": msg.message,
                    "isDeveloperFacing": msg.isDeveloperFacing,
                },)
            )


    def onJsonViewOfSystemChanged(self, json):
        self.viewOfCumulusSystem = json.toSimple()
