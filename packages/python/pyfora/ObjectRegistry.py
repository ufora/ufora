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

import pyfora.TypeDescription as TypeDescription
import base64

class ObjectRegistry(object):
    def __init__(self):
        self._nextObjectID = 0
        self.objectIdToObjectDefinition = {}

    def getDefinition(self, objectId):
        return self.objectIdToObjectDefinition[objectId]

    def allocateObject(self):
        "get a unique id for an object to be inserted later in the registry"
        objectId = self._nextObjectID
        self._nextObjectID += 1
        return objectId

    def definePrimitive(self, objectId, primitive):
        if isinstance(primitive, str):
            primitive = base64.b64encode(primitive)
        self.objectIdToObjectDefinition[objectId] = primitive

    def defineTuple(self, objectId, memberIds):
        self.objectIdToObjectDefinition[objectId] = TypeDescription.Tuple(memberIds)

    def defineList(self, objectId, memberIds):
        self.objectIdToObjectDefinition[objectId] = TypeDescription.List(memberIds)

    def defineFile(self, objectId, text, path):
        self.objectIdToObjectDefinition[objectId] = TypeDescription.File(path, text)

    def defineDict(self, objectId, keyIds, valueIds):
        self.objectIdToObjectDefinition[objectId] = TypeDescription.Dict(keyIds=keyIds,
                                                                         valueIds=valueIds)

    def defineRemotePythonObject(self, objectId, computedValueArg):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.RemotePythonObject(computedValueArg)

    def defineBuiltinExceptionInstance(self, objectId, typename, argsId):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.BuiltinExceptionInstance(typename, argsId)

    def defineNamedSingleton(self, objectId, singletonName):
        self.objectIdToObjectDefinition[objectId] = TypeDescription.NamedSingleton(singletonName)

    def defineFunction(self, objectId, sourceFileId, lineNumber, scopeIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        """
        freeVariableMemberAccessChainsToId = \
            self._processFreeVariableMemberAccessChainResolution(scopeIds)

        self.objectIdToObjectDefinition[objectId] = TypeDescription.FunctionDefinition(
            sourceFileId=sourceFileId,
            lineNumber=lineNumber,
            freeVariableMemberAccessChainsToId=freeVariableMemberAccessChainsToId
            )

    def defineClass(self, objectId, sourceFileId, lineNumber, scopeIds, baseClassIds):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        baseClassIds: a list of ids representing (immediate) base classes
        """
        freeVariableMemberAccessChainsToId = \
            self._processFreeVariableMemberAccessChainResolution(
                scopeIds
                )

        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.ClassDefinition(
                sourceFileId=sourceFileId,
                lineNumber=lineNumber,
                freeVariableMemberAccessChainsToId=freeVariableMemberAccessChainsToId,
                baseClassIds=baseClassIds
                )

    def defineUnconvertible(self, objectId):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.Unconvertible()

    def _processFreeVariableMemberAccessChainResolution(
            self,
            freeVariableMemberAccessChainsToId
            ):
        return {
            chainAsString: resolutionId
            for chainAsString, resolutionId in freeVariableMemberAccessChainsToId.iteritems()
            }

    def defineClassInstance(self, objectId, classId, classMemberNameToClassMemberId):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.ClassInstanceDescription(
                classId=classId,
                classMemberNameToClassMemberId=classMemberNameToClassMemberId
                )

    def defineInstanceMethod(self, objectId, instanceId, methodName):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.InstanceMethod(
                instanceId=instanceId,
                methodName=methodName
                )

    def defineWithBlock(self,
                        objectId,
                        freeVariableMemberAccessChainsToId,
                        sourceFileId,
                        lineNumber):
        self.objectIdToObjectDefinition[objectId] = \
            TypeDescription.WithBlockDescription(
                freeVariableMemberAccessChainsToId,
                sourceFileId,
                lineNumber
                )

    def computeDependencyGraph(self, objectId):
        graphOfIds = dict()
        self._populateGraphOfIds(graphOfIds, objectId)
        return graphOfIds

    def _populateGraphOfIds(self, graphOfIds, objectId):
        dependentIds = self._computeDependentIds(objectId)
        graphOfIds[objectId] = dependentIds

        for objectId in dependentIds:
            if objectId not in graphOfIds:
                self._populateGraphOfIds(graphOfIds, objectId)

    def _computeDependentIds(self, objectId):
        objectDefinition = self.objectIdToObjectDefinition[objectId]

        if TypeDescription.isPrimitive(objectDefinition) or \
                isinstance(objectDefinition,
                           (TypeDescription.File, TypeDescription.RemotePythonObject,
                            TypeDescription.NamedSingleton, list,
                            TypeDescription.Unconvertible)):
            return []
        elif isinstance(objectDefinition, (TypeDescription.BuiltinExceptionInstance)):
            return [objectDefinition.argsId]
        elif isinstance(objectDefinition, (TypeDescription.List, TypeDescription.Tuple)):
            return objectDefinition.memberIds
        elif isinstance(objectDefinition,
                        (TypeDescription.FunctionDefinition, TypeDescription.ClassDefinition)):
            tr = objectDefinition.freeVariableMemberAccessChainsToId.values()
            tr.append(objectDefinition.sourceFileId)
            return tr
        elif isinstance(objectDefinition, TypeDescription.InstanceMethod):
            return [objectDefinition.instanceId]
        elif isinstance(objectDefinition, TypeDescription.ClassInstanceDescription):
            tr = [objectDefinition.classId]
            tr.extend(
                self._computeDependentIds(
                    objectDefinition.classId
                    )
                )
            classMemberIds = \
                objectDefinition.classMemberNameToClassMemberId.values()
            tr.extend(classMemberIds)

            return tr
        elif isinstance(objectDefinition, TypeDescription.Dict):
            return objectDefinition.keyIds + objectDefinition.valueIds
        elif isinstance(objectDefinition, TypeDescription.WithBlockDescription):
            tr = objectDefinition.freeVariableMemberAccessChainsToId.values()
            tr.append(objectDefinition.sourceFileId)

            return tr
        else:
            assert False, "don't know what to do with %s" % type(objectDefinition)

