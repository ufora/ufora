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

import pyfora.LongTermObjectRegistry as LongTermObjectRegistry
import pyfora.LongTermObjectRegistryIncrement as LongTermObjectRegistryIncrement
import pyfora.TypeDescription as TypeDescription
import base64


class PathWrapper(object):
    def __init__(self, path):
        self.path = path

    def __hash__(self):
        return hash(self.path)


def isHashable(pyObject):
    try:
        hash(pyObject)
        return True
    except:
        return False


class ObjectRegistry(object):
    def __init__(self, longTermObjectRegistry=None):
        self._nextObjectID = 0

        # contains objects already defined on the server, which
        # we assume don't change, like files and class definitions
        if longTermObjectRegistry is None:
            longTermObjectRegistry = \
                LongTermObjectRegistry.LongTermObjectRegistry()
        self.longTermObjectRegistry = longTermObjectRegistry

        # essentially a dict { objectId: ObjectDefinition } of objects eventually
        # to be merged into self.longTermObjectRegistry. gets merged on calls to 
        # self.onConverted
        self.longTermObjectRegistryIncrement = \
            LongTermObjectRegistryIncrement.LongTermObjectRegistryIncrement()

        # holds objects which are not in the longTermObjectRegistry
        # gets (at least partially) purged on calls to self.onConverted()
        self.shortTermObjectIdToObjectDefinition = {}

    def onConverted(self, objectId, dependencyGraph):
        self.longTermObjectRegistry.mergeIncrement(
            self.longTermObjectRegistryIncrement)

        # if objectId (or any of its dependencies) is short term, drop it.
        # you might think that another object out there could depend
        # on this dropped one, but we don't allow this.
        # other objects can only depend on *new* object ids
        # for the same short term python object (which means more than one walk 
        # for a python object could happen)
        for objId in dependencyGraph:
            self.shortTermObjectIdToObjectDefinition.pop(objId, None)

    def longTermObjectId(self, pyObject):
        try:
            if self.longTermObjectRegistry.hasObject(pyObject):
                return self.longTermObjectRegistry.getObject(pyObject).objectId
            elif self.longTermObjectRegistryIncrement.hasObject(pyObject):
                return self.longTermObjectRegistryIncrement.getObject(pyObject).objectId
        except TypeError: # unhashable type
            return None

    def getDefinition(self, objectId):
        if self.longTermObjectRegistry.hasObjectId(objectId):
            return self.longTermObjectRegistry\
                       .getObjectDefinitionByObjectId(objectId)
        elif self.longTermObjectRegistryIncrement.hasObjectId(objectId):
            return self.longTermObjectRegistryIncrement\
                       .getObjectDefinitionByObjectId(objectId)

        return self.shortTermObjectIdToObjectDefinition[objectId]

    def allocateObject(self):
        "get a unique id for an object to be inserted later in the registry"
        objectId = self._nextObjectID
        self._nextObjectID += 1
        return objectId

    def idForFileAndText(self, path, text):
        pathWrapper = PathWrapper(path)

        longTermObjectIdOrNone = self.longTermObjectId(pathWrapper)
        if longTermObjectIdOrNone is not None:
            return longTermObjectIdOrNone

        objectId = self.allocateObject()
        objectDefinition = TypeDescription.File(path, text)

        self.longTermObjectRegistryIncrement.pushIncrementEntry(
            pathWrapper, objectId, objectDefinition)

        return objectId

    def definePrimitive(self, objectId, primitive, isLongTerm):
        if isinstance(primitive, str):
            primitive = base64.b64encode(primitive)

        self._pushToLongOrShortTermStorage(
            pyObject=primitive,
            objectId=objectId,
            objectDefinition=primitive,
            isLongTerm=isLongTerm or isinstance(primitive, (type(None), bool))
            )

    def defineTuple(self, pyObject, objectId, memberIds, isLongTerm):
        objectDefinition = TypeDescription.Tuple(memberIds)

        self._pushToLongOrShortTermStorage(
            pyObject=pyObject,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineList(self, objectId, memberIds):
        self.shortTermObjectIdToObjectDefinition[objectId] = \
            TypeDescription.List(memberIds)

    def defineDict(self, objectId, keyIds, valueIds):
        self.shortTermObjectIdToObjectDefinition[objectId] = \
            TypeDescription.Dict(keyIds=keyIds,
                                 valueIds=valueIds)

    def defineRemotePythonObject(self, objectId, computedValueArg, isLongTerm=False):
        objectDefinition = TypeDescription.RemotePythonObject(computedValueArg)

        self._pushToLongOrShortTermStorage(
            pyObject=computedValueArg,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineBuiltinExceptionInstance(self,
                                       objectId,
                                       builtinExceptionInstance,
                                       typename,
                                       argsId,
                                       isLongTerm):
        objectDefinition = TypeDescription.BuiltinExceptionInstance(typename, argsId)

        self._pushToLongOrShortTermStorage(
            pyObject=builtinExceptionInstance,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineNamedSingleton(self, objectId, singletonName, pyObject, isLongTerm):
        objectDefinition = TypeDescription.NamedSingleton(singletonName)

        self._pushToLongOrShortTermStorage(
            pyObject=pyObject,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineFunction(self,
                       function,
                       objectId,
                       sourceFileId,
                       lineNumber,
                       scopeIds,
                       isLongTerm):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        """
        objectDefinition = TypeDescription.FunctionDefinition(
            sourceFileId=sourceFileId,
            lineNumber=lineNumber,
            freeVariableMemberAccessChainsToId=scopeIds
            )

        self._pushToLongOrShortTermStorage(
            pyObject=function,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineClass(self,
                    cls,
                    objectId,
                    sourceFileId,
                    lineNumber,
                    scopeIds,
                    baseClassIds,
                    isLongTerm):
        """
        scopeIds: a dict freeVariableMemberAccessChain -> id
        baseClassIds: a list of ids representing (immediate) base classes
        """
        objectDefinition = TypeDescription.ClassDefinition(
            sourceFileId=sourceFileId,
            lineNumber=lineNumber,
            freeVariableMemberAccessChainsToId=scopeIds,
            baseClassIds=baseClassIds
            )

        self._pushToLongOrShortTermStorage(
            pyObject=cls,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm
            )

    def defineUnconvertible(self, objectId):
        self.shortTermObjectIdToObjectDefinition[objectId] = \
            TypeDescription.Unconvertible()

    def defineClassInstance(self,
                            pyObject,
                            objectId,
                            classId,
                            classMemberNameToClassMemberId,
                            isLongTerm):
        objectDefinition = TypeDescription.ClassInstanceDescription(
            classId=classId,
            classMemberNameToClassMemberId=classMemberNameToClassMemberId
            )

        self._pushToLongOrShortTermStorage(
            pyObject=pyObject,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm and isHashable(pyObject)
            )

    def defineInstanceMethod(self,
                             pyObject,
                             objectId,
                             instanceId,
                             methodName,
                             isLongTerm):
        objectDefinition = TypeDescription.InstanceMethod(
            instanceId=instanceId,
            methodName=methodName
            )
        
        self._pushToLongOrShortTermStorage(
            pyObject=pyObject,
            objectId=objectId,
            objectDefinition=objectDefinition,
            isLongTerm=isLongTerm and isHashable(pyObject)
            )

    def defineWithBlock(self,
                        objectId,
                        freeVariableMemberAccessChainsToId,
                        sourceFileId,
                        lineNumber):
        self.shortTermObjectIdToObjectDefinition[objectId] = \
            TypeDescription.WithBlockDescription(
                freeVariableMemberAccessChainsToId,
                sourceFileId,
                lineNumber
                )

    def computeDependencyGraph(self, objectId):
        graphOfIds = dict()
        self._populateGraphOfIds(graphOfIds, objectId)
        return graphOfIds

    def _pushToLongOrShortTermStorage(self,
                                      pyObject,
                                      objectId,
                                      objectDefinition,
                                      isLongTerm):
        if isLongTerm:
            self.longTermObjectRegistryIncrement.pushIncrementEntry(
                pyObject,
                objectId,
                objectDefinition
                )
        else:
            self.shortTermObjectIdToObjectDefinition[objectId] = \
                objectDefinition                

    def _populateGraphOfIds(self, graphOfIds, objectId):
        dependentIds = self._computeDependentIds(objectId)
        graphOfIds[objectId] = dependentIds

        for objectId in dependentIds:
            if objectId not in graphOfIds:
                self._populateGraphOfIds(graphOfIds, objectId)

    def _computeDependentIds(self, objectId):
        objectDefinition = self.getDefinition(objectId)

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

