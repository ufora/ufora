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
    import SubscribableObject, ExposedFunction


class PyforaObjectConverter(SubscribableObject):
    def __init__(self, id, cumulus_env, _):
        super(PyforaObjectConverter, self).__init__(id, cumulus_env)


    @ExposedFunction(expandArgs=True)
    def initialize(self, purePythonMDSAsJson):
        return self.object_converter.initialize(purePythonMDSAsJson)


    #def hasObjectId(self, objectId):
        #return objectId in self.objectIdToIvc_


    #def getIvcFromObjectId(self, objectId):
        #return self.objectIdToIvc_[objectId]


    #def unwrapPyforaDictToDictOfAssignedVars(self, dictIVC):
        #"""Take a Pyfora dictionary, and return a dict {string->IVC}.
           #Returns None if not possible."""
        #return self.converter_[0].unwrapPyforaDictToDictOfAssignedVars(dictIVC)


    #def unwrapPyforaTupleToTuple(self, tupleIVC):
        #"""Take a Pyfora tuple, and return a tuple {IVC}.
           #Returns None if not possible."""
        #return self.converter_[0].unwrapPyforaTupleToTuple(tupleIVC)


    @ExposedFunction(expandArgs=True)
    def convert(self, objectId, objectIdToObjectDefinition):
        return self.object_converter.convert(objectId, objectIdToObjectDefinition)


