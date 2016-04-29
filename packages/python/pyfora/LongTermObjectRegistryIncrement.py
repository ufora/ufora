#   Copyright 2016 Ufora Inc.
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


import pyfora.LongTermRegistryEntry as LongTermRegistryEntry
from pyfora.LongTermObjectRegistryKey import LongTermObjectRegistryKey


class LongTermObjectRegistryIncrement(object):
    def __init__(self):
        self.registeredObjectToEntry = {}
        self.objectIdToObjectDefinition = {}

    def pushIncrementEntry(self, pyObject, objectId, objectDefinition):
        key = self._keyFor(pyObject)

        self.registeredObjectToEntry[key] = \
            LongTermRegistryEntry.LongTermRegistryEntry(
                contents=objectDefinition,
                objectId=objectId)
        self.objectIdToObjectDefinition[objectId] = objectDefinition

    def hasObjectId(self, objectId):
        return objectId in self.objectIdToObjectDefinition

    def getObjectDefinitionByObjectId(self, objectId):
        return self.objectIdToObjectDefinition[objectId]

    def hasObject(self, pyObject):
        return self._keyFor(pyObject) in self.registeredObjectToEntry

    def getObject(self, pyObject):
        return self.registeredObjectToEntry[self._keyFor(pyObject)]

    def _keyFor(self, pyObject):
        return LongTermObjectRegistryKey.keyFor(pyObject)
