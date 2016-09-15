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

import ufora.FORA.python.ForaValue as ForaValue
import ufora.FORA.python.ModuleImporter as ModuleImporter
import ufora.FORA.python.PurePython.NativeConverterAdaptor as NativeConverterAdaptor
import ufora.FORA.python.ModuleDirectoryStructure as ModuleDirectoryStructure
import ufora.FORA.python.PurePython.PyforaSingletonAndExceptionConverter as PyforaSingletonAndExceptionConverter
import ufora.FORA.python.PurePython.PyforaToJsonTransformer as PyforaToJsonTransformer
import ufora.native.FORA as ForaNative

import pyfora.ModuleLevelObjectIndex as ModuleLevelObjectIndex
import pyfora.TypeDescription as TypeDescription
import pyfora.StronglyConnectedComponents as StronglyConnectedComponents
import pyfora.BinaryObjectRegistry as BinaryObjectRegistry

import pyfora
import base64
import os
import logging

import ufora.native.FORA as ForaNative

Symbol_uninitialized = ForaNative.makeSymbol("PyforaUninitializedVariable")
Symbol_invalid = ForaNative.makeSymbol("PyforaInvalidVariable")
Symbol_unconvertible = ForaNative.makeSymbol("PyforaUnconvertibleValue")

class UnconvertibleToken:
    pass

def isUnconvertibleValueTuple(implVal):
    if isinstance(implVal, ForaNative.ImplValContainer) and implVal.isTuple() and len(implVal) == 1:
        if implVal.getTupleNames()[0] == "PyforaUnconvertibleValue":
            return True
    return False

def convertNativePythonToForaConversionError(err, path):
    """Convert a ForaNative.PythonToForaConversionError to a python version of the exception"""
    return pyfora.PythonToForaConversionError(
        err.error,
        trace=[{
            'path': path,
            'line': err.range.start.line
            }]
        )


class Converter(object):
    def __init__(self,
                 nativeConstantConverter=None,
                 nativeListConverter=None,
                 nativeTupleConverter=None,
                 nativeDictConverter=None,
                 singletonAndExceptionConverter=None,
                 vdmOverride=None,
                 purePythonModuleImplVal=None,
                 foraBuiltinsImplVal=None
                 ):
        self.convertedValues = {}

        self.singletonAndExceptionConverter = singletonAndExceptionConverter

        self.pyforaBoundMethodClass = purePythonModuleImplVal.getObjectMember("PyBoundMethod")

        self.nativeConstantConverter = nativeConstantConverter
        self.nativeListConverter = nativeListConverter
        self.nativeTupleConverter = nativeTupleConverter
        
        builtinMemberMapping = Converter.computeBuiltinMemberMapping(
            purePythonModuleImplVal=purePythonModuleImplVal,
            foraBuiltinsImplVal=foraBuiltinsImplVal
            )

        self.nativeConverterAdaptor = NativeConverterAdaptor.NativeConverterAdaptor(
            nativeConstantConverter=nativeConstantConverter,
            nativeDictConverter=nativeDictConverter,
            nativeTupleConverter=nativeTupleConverter,
            nativeListConverter=nativeListConverter,
            vdmOverride=vdmOverride,
            builtinMemberMapping=builtinMemberMapping,
            purePythonModuleImplVal=purePythonModuleImplVal
            )

        self.convertedStronglyConnectedComponents = set()

    def teardown(self):
        self.nativeConverterAdaptor.teardown()

    @staticmethod
    def computeBuiltinMemberMapping(purePythonModuleImplVal, foraBuiltinsImplVal):
        builtinMemberMapping = {}

        builtinMemberMapping.update(
            Converter.computeMemberMapping(
                purePythonModuleImplVal
                )
            )

        builtinMemberMapping.update(
            Converter.computeMemberMapping(
                foraBuiltinsImplVal
                )
            )

        builtinMemberMapping['purePython'] = purePythonModuleImplVal
        builtinMemberMapping['builtin'] = foraBuiltinsImplVal

        return builtinMemberMapping

    @staticmethod
    def computeMemberMapping(purePythonImplVal):
        objectMembers = purePythonImplVal.objectMembers
        tr = {}
        for memberName in objectMembers:
            objectMember = purePythonImplVal.getObjectMember(memberName)

            # TODO anybody: we're missing `builtin.Exception` here, since
            # it is from a computation which FS1 simulator can't handle
            # (from the source: `Exception: `Exception`();`)
            if objectMember is not None:
                tr[memberName] = objectMember

        return tr

    def extractWrappedForaConstant(self, value):
        """Convenience method for testing. If 'value' is an ImplVal, get @m out of it."""
        if isinstance(value, ForaValue.FORAValue):
            value = value.implVal_
        if not isinstance(value, ForaNative.ImplValContainer):
            return value

        return value.getObjectLexicalMember("@m")[0].pyval

    def convert(self, objectId, objectRegistry, callback):
        try:
            callback(self.convertDirectly(objectId, objectRegistry))
        except pyfora.PythonToForaConversionError as e:
            callback(e)

    def convertDirectly(self, objectId, objectRegistry):
        dependencyGraph = objectRegistry.computeDependencyGraph(objectId)
        objectIdToObjectDefinition = {
            objId: objectRegistry.getDefinition(objId)
            for objId in dependencyGraph.iterkeys()
            }

        convertedValue = self._convert(objectId, dependencyGraph, objectIdToObjectDefinition)
        self.convertedValues[objectId] = convertedValue
        return convertedValue

    def _convert(self, objectId, dependencyGraph, objectIdToObjectDefinition):
        objectDefinition = objectIdToObjectDefinition[objectId]
        if TypeDescription.isPrimitive(objectDefinition) or isinstance(objectDefinition, list):
            return self.convertPrimitive(objectDefinition)
        elif isinstance(objectDefinition, TypeDescription.RemotePythonObject):
            return self.convertRemotePythonObject(objectDefinition)
        elif isinstance(objectDefinition, TypeDescription.NamedSingleton):
            return self.convertNamedSingleton(objectDefinition)
        elif isinstance(objectDefinition, TypeDescription.BuiltinExceptionInstance):
            return self.convertBuiltinExceptionInstance(
                objectDefinition
                )
        elif isinstance(objectDefinition,
                        (TypeDescription.FunctionDefinition,
                         TypeDescription.ClassDefinition,
                         TypeDescription.ClassInstanceDescription,
                         TypeDescription.InstanceMethod)
                       ):
            return (
                self.convertObjectWithDependencies(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.List):
            return (
                self.convertList(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.PackedHomogenousData):
            return (
                self.convertPackedHomogenousDataAsList(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.Tuple):
            return (
                self.convertTuple(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.Dict):
            return (
                self.convertDict(
                    objectId,
                    objectDefinition,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.WithBlockDescription):
            return (
                self.convertObjectWithDependencies(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
                )
        elif isinstance(objectDefinition, TypeDescription.Unconvertible):
            return self.convertUnconvertibleValue(objectId, objectDefinition.module_path)
        else:
            raise pyfora.PythonToForaConversionError(
                "don't know how to convert %s of type %s" % (
                    objectDefinition, type(objectDefinition)
                    )
                )

    def convertNamedSingleton(self, objectDefinition):
        if self.singletonAndExceptionConverter is None:
            logging.error("Can't convert %s without a converter", objectDefinition.singletonName)

        singleton = self.singletonAndExceptionConverter.convertSingletonByName(
            objectDefinition.singletonName
            )

        if singleton is None:
            raise pyfora.PythonToForaConversionError(
                "No singleton named %s" % objectDefinition.singletonName
                )

        return singleton

    def convertBuiltinExceptionInstance(self, objectDefinition):
        args = self.convertedValues[objectDefinition.argsId]

        return self.singletonAndExceptionConverter.instantiateException(
            objectDefinition.builtinExceptionTypeName,
            args
            )

    def convertRemotePythonObject(self, objectDefinition):
        computedValueArg = objectDefinition.computedValueArgument

        if isinstance(computedValueArg, int):
            #then this is an object we've already seen. We can assume it's here,
            #because the only way this can happen is to return an object to the server
            #that we've converted, and then have that object be used again in another
            #computation
            return self.convertedValues[computedValueArg]
        else:
            return computedValueArg

    def convertDict(self, dictId, objectDefinition, dependencyGraph, objectIdToObjectDefinition):
        self._convertListMembers(dictId, dependencyGraph, objectIdToObjectDefinition)
        convertedKeysAndVals = {
            self.convertedValues[keyId]: self.convertedValues[valId]
            for keyId, valId in zip(objectDefinition.keyIds, objectDefinition.valueIds)
            }

        return self.nativeConverterAdaptor.createDict(convertedKeysAndVals)

    def convertUnconvertibleValue(self, objectId, module_path):
        # uh, yeah ... this guy probably needs a better name. Sorry.
        tr = ForaNative.CreateNamedTuple((tuple(module_path) if module_path is not None else None,), ("PyforaUnconvertibleValue",))
        self.convertedValues[objectId] = tr
        return tr

    def convertPrimitive(self, value):
        if isinstance(value, list):
            return self.nativeConverterAdaptor.createListOfPrimitives(value)

        return self.nativeConverterAdaptor.convertConstant(value)

    def _assertContainerDoesNotReferenceItself(self,
                                               containerId,
                                               dependencyGraph,
                                               stronglyConnectedComponents):
        assert containerId in stronglyConnectedComponents[-1]

        if len(stronglyConnectedComponents[-1]) > 1 or \
           containerId in dependencyGraph[containerId]:
            raise pyfora.PythonToForaConversionError(
                "don't know how to convert lists or tuples which reference themselves"
                )

    def convertPackedHomogenousDataAsList(self, listId, dependencyGraph, objectIdToObjectDefinition):
        packedData = objectIdToObjectDefinition[listId]

        return self.nativeConverterAdaptor.createListFromPackedData(
            self.nativeConstantConverter,
            self.nativeTupleConverter,
            packedData.dtype, 
            packedData.dataAsBytes
            )

    def convertList(self, listId, dependencyGraph, objectIdToObjectDefinition):
        self._convertListMembers(listId, dependencyGraph, objectIdToObjectDefinition)
        memberIds = objectIdToObjectDefinition[listId].memberIds

        return self.nativeConverterAdaptor.createList(
            [self.convertedValues[memberId] for memberId in memberIds]
            )

    def convertTuple(self, tupleId, dependencyGraph, objectIdToObjectDefinition):
        self._convertListMembers(tupleId, dependencyGraph, objectIdToObjectDefinition)
        memberIds = objectIdToObjectDefinition[tupleId].memberIds

        return self.nativeConverterAdaptor.createTuple(
            [self.convertedValues[memberId] for memberId in memberIds]
            )


    def _convertListMembers(self, listId, dependencyGraph, objectIdToObjectDefinition):
        stronglyConnectedComponents = \
            StronglyConnectedComponents.stronglyConnectedComponents(
                dependencyGraph
                )

        self._assertContainerDoesNotReferenceItself(
            listId,
            dependencyGraph,
            stronglyConnectedComponents
            )

        for stronglyConnectedComponent in stronglyConnectedComponents[:-1]:
            self.convertStronglyConnectedComponent(
                dependencyGraph,
                stronglyConnectedComponent,
                objectIdToObjectDefinition
                )

    def convertObjectWithDependencies(self, objectId, dependencyGraph, objectIdToObjectDefinition):
        if objectId in self.convertedValues:
            return self.convertedValues[objectId]

        stronglyConnectedComponents = \
            StronglyConnectedComponents.stronglyConnectedComponents(
                dependencyGraph
                )

        for stronglyConnectedComponent in stronglyConnectedComponents:
            self.convertStronglyConnectedComponent(
                dependencyGraph,
                stronglyConnectedComponent,
                objectIdToObjectDefinition
                )

        return self.convertedValues[objectId]

    def convertStronglyConnectedComponent(self,
                                          dependencyGraph,
                                          stronglyConnectedComponent,
                                          objectIdToObjectDefinition):
        if stronglyConnectedComponent in self.convertedStronglyConnectedComponents:
            return

        if len(stronglyConnectedComponent) == 1:
            self.convertStronglyConnectedComponentWithOneNode(
                dependencyGraph,
                stronglyConnectedComponent,
                objectIdToObjectDefinition
                )
        else:
            self.convertStronglyConnectedComponentWithMoreThanOneNode(
                objectIdToObjectDefinition,
                stronglyConnectedComponent
                )

        self.convertedStronglyConnectedComponents.add(stronglyConnectedComponent)

    def convertStronglyConnectedComponentWithMoreThanOneNode(self,
                                                             objectIdToObjectDefinition,
                                                             stronglyConnectedComponent):

        implValAndMemberToObjectIdMap = self.nativeConverterAdaptor.convertMutuallyRecursiveObjects(
            objectIdToObjectDefinition,
            stronglyConnectedComponent,
            self.convertedValues
            )

        self.registerObjectMembers(
            implValAndMemberToObjectIdMap.implVal,
            implValAndMemberToObjectIdMap.memberToObjectIdMap
            )

    def registerObjectMembers(self, objectImplVal, renamedObjectMapping):
        for objectId, memberName in renamedObjectMapping.iteritems():
            memberImplValOrNone = objectImplVal.getObjectMember(memberName)

            if memberImplValOrNone is None:
                raise pyfora.PythonToForaConversionError(
                    ("An internal error occurred: " +
                     "getObjectMember unexpectedly returned None")
                    )

            self.convertedValues[objectId] = memberImplValOrNone

    def convertStronglyConnectedComponentWithOneNode(self,
                                                     dependencyGraph,
                                                     stronglyConnectedComponent,
                                                     objectIdToObjectDefinition):
        objectId = stronglyConnectedComponent[0]

        objectDefinition = objectIdToObjectDefinition[objectId]

        if TypeDescription.isPrimitive(objectDefinition) or isinstance(objectDefinition, list):
            self.convertedValues[objectId] = self.convertPrimitive(objectDefinition)

        elif isinstance(objectDefinition, (TypeDescription.FunctionDefinition,
                                           TypeDescription.ClassDefinition)):
            if isinstance(objectDefinition, TypeDescription.ClassDefinition):
                for baseId in objectDefinition.baseClassIds:
                    if baseId not in self.convertedValues:
                        self._convert(baseId,
                                      dependencyGraph,
                                      objectIdToObjectDefinition)
                    assert baseId in self.convertedValues
            self.convertStronglyConnectedComponentWithOneFunctionOrClass(
                objectId,
                objectDefinition,
                objectIdToObjectDefinition
                )

        elif isinstance(objectDefinition, TypeDescription.ClassInstanceDescription):
            self.convertClassInstanceDescription(
                objectId,
                objectDefinition
                )

        elif isinstance(objectDefinition, TypeDescription.List):
            self.convertedValues[objectId] = self.convertList(
                objectId,
                self._computeRestrictedGraph(
                    objectId,
                    dependencyGraph
                    ),
                objectIdToObjectDefinition
                )

        elif isinstance(objectDefinition, TypeDescription.Tuple):
            self.convertedValues[objectId] = self.convertTuple(
                objectId,
                self._computeRestrictedGraph(
                    objectId,
                    dependencyGraph
                    ),
                objectIdToObjectDefinition
                )

        elif isinstance(objectDefinition, TypeDescription.Dict):
            self.convertedValues[objectId] = self.convertDict(
                objectId,
                objectDefinition,
                self._computeRestrictedGraph(
                    objectId,
                    dependencyGraph
                    ),
                objectIdToObjectDefinition
                )

        elif isinstance(objectDefinition, TypeDescription.File):
            self.convertedValues[objectId] = self.convertFile(objectDefinition)

        elif isinstance(objectDefinition, TypeDescription.RemotePythonObject):
            self.convertedValues[objectId] = self.convertRemotePythonObject(objectDefinition)

        elif isinstance(objectDefinition, TypeDescription.BuiltinExceptionInstance):
            self.convertedValues[objectId] = self.convertBuiltinExceptionInstance(objectDefinition)

        elif isinstance(objectDefinition, TypeDescription.NamedSingleton):
            self.convertedValues[objectId] = self.convertNamedSingleton(objectDefinition)

        elif isinstance(objectDefinition, TypeDescription.WithBlockDescription):
            self.convertWithBlock(objectId,
                                  objectDefinition,
                                  objectIdToObjectDefinition)

        elif isinstance(objectDefinition, TypeDescription.InstanceMethod):
            self.convertedValues[objectId] = self.convertInstanceMethod(objectId,
                                                                        objectIdToObjectDefinition)

        elif isinstance(objectDefinition, TypeDescription.Unconvertible):
            self.convertUnconvertibleValue(objectId, objectDefinition.module_path)

        elif isinstance(objectDefinition, TypeDescription.PackedHomogenousData):
            self.convertedValues[objectId] = self.convertPackedHomogenousDataAsList(
                    objectId,
                    dependencyGraph,
                    objectIdToObjectDefinition
                    )
        else:
            assert False, "haven't gotten to this yet %s" % type(objectDefinition)

    def convertInstanceMethod(self, objectId, objectIdToObjectDefinition):
        objectDef = objectIdToObjectDefinition[objectId]
        instance = self.convertedValues[objectDef.instanceId]
        bound = instance.getObjectMember(objectDef.methodName)
        assert bound is not None
        return bound

    def convertWithBlock(self, objectId, withBlockDescription, objectIdToObjectDefinition):
        tr = self.nativeConverterAdaptor.convertWithBlock(
            withBlockDescription,
            objectIdToObjectDefinition,
            self.convertedValues
            )

        self.convertedValues[objectId] = tr

        return tr

    def convertFile(self, objectDefinition):
        return objectDefinition.text

    def _computeRestrictedGraph(self, objectId, dependencyGraph):
        """Compute the subgraph of nodes reachable from `objectId`"""
        tr = dict()

        stack = [objectId]
        visited = set()

        while stack:
            toVisit = stack.pop()
            if toVisit not in visited:
                tr[toVisit] = dependencyGraph[toVisit]
                stack.extend(dependencyGraph[toVisit])
                visited.add(toVisit)

        return tr

    def convertClassInstanceDescription(self, objectId, classInstanceDescription):
        if objectId in self.convertedValues:
            return

        self.nativeConverterAdaptor.convertClassInstanceDescription(
            objectId,
            classInstanceDescription,
            self.convertedValues
            )

    def convertStronglyConnectedComponentWithOneFunctionOrClass(self,
                                                                objectId,
                                                                classOrFunctionDefinition,
                                                                objectIdToObjectDefinition):
        self.convertedValues[objectId] = \
            self.nativeConverterAdaptor.convertClassOrFunctionDefinitionWithNoDependencies(
                classOrFunctionDefinition,
                objectIdToObjectDefinition,
                self.convertedValues)

    def unwrapPyforaDictToDictOfAssignedVars(self, dictIVC):
        """Take a Pyfora dictionary, and return a dict {string->IVC}. Returns None if not possible."""
        pyforaDict = self.nativeConverterAdaptor.invertDict(dictIVC)
        if pyforaDict is None:
            return None

        res = {}

        for pyforaKey, pyforaValue in pyforaDict.iteritems():
            if pyforaValue != Symbol_uninitialized and pyforaValue != Symbol_invalid:
                maybePyforaKeyString = self.nativeConverterAdaptor.invertForaConstant(pyforaKey)
                if isinstance(maybePyforaKeyString, tuple) and isinstance(maybePyforaKeyString[0], str):
                    res[maybePyforaKeyString[0]] = pyforaValue
                else:
                    return None

        return res

    def unwrapPyforaTupleToTuple(self, tupleIVC):
        pyforaTuple = self.nativeConverterAdaptor.invertTuple(tupleIVC)
        if pyforaTuple is None:
            return None

        res = tuple([pyforaValue for pyforaValue in pyforaTuple])
        return res

    def transformPyforaImplval(self, implval, stream, vectorContentsExtractor, maxBytecount=None):
        hashToObjectId = {}
        fileToObjectId = {}
        anyNeedLoading = [False]

        def transform(implval):
            if implval.hash in hashToObjectId:
                return hashToObjectId[implval.hash]

            objId = stream.allocateObject()
            hashToObjectId[implval.hash] = objId

            transformBody(objId, implval)

            if maxBytecount is not None and stream.bytecount() > maxBytecount:
                raise PyforaToJsonTransformer.HaltTransformationException()

            return objId

        def transformFile(path, text):
            if (path,text) in fileToObjectId:
                return fileToObjectId[(path,text)]

            objId = stream.allocateObject()
            fileToObjectId[(path,text)] = objId

            stream.defineFile(objId, text, path)

            return objId

        def transformBody(objId, implval):
            if isUnconvertibleValueTuple(implval):
                path = implval[0].pyval
                stream.defineUnconvertible(objId, path)
                return objId

            if implval.isString():
                value = (implval.pyval,)
            else:
                value = self.nativeConverterAdaptor.invertForaConstant(implval)

            if value is not None:
                if isinstance(value, tuple):
                    #this is a simple constant
                    stream.definePrimitive(objId, value[0])
                    return objId
                else:
                    #this is a vector that represents a string
                    assert isinstance(value, ForaNative.ImplValContainer)

                    if len(value) == 0:
                        stream.definePrimitive(objId, "")
                        return objId

                    assert value.isVectorOfChar(), value

                    contents = vectorContentsExtractor(value)

                    if contents is None:
                        anyNeedLoading[0] = True
                        stream.definePrimitive(objId, "")
                        return objId
                    else:
                        assert 'string' in contents
                        stream.definePrimitive(objId, contents['string'])
                        return objId

            if self.singletonAndExceptionConverter is not None:
                value = self.singletonAndExceptionConverter.convertInstanceToSingletonName(implval)
                if value is not None:
                    stream.defineNamedSingleton(objId, value)
                    return objId

                value = self.singletonAndExceptionConverter.convertExceptionInstance(implval)
                if value is not None:
                    stream.defineBuiltinExceptionInstance(objId, value[0], transform(value[1]))
                    return objId

                value = self.singletonAndExceptionConverter.convertPyAbortExceptionInstance(
                    implval
                    )
                if value is not None:
                    stream.definePyAbortException(objId, value[0], transform(value[1]))
                    return objId

            value = self.nativeConverterAdaptor.invertTuple(implval)
            if value is not None:
                tupleIds = [transform(x) for x in value]
                stream.defineTuple(objId, tupleIds)
                return objId

            value = self.nativeConverterAdaptor.invertDict(implval)
            if value is not None:
                stream.defineDict(
                    objId,
                    [transform(k) for k in value.keys()],
                    [transform(v) for v in value.values()]
                    )
                return objId

            listItemsAsVector = self.nativeConverterAdaptor.invertList(implval)
            if listItemsAsVector is not None:
                contents = vectorContentsExtractor(listItemsAsVector)

                if contents is None:
                    stream.defineList(objId, [])
                    anyNeedLoading[0] = True
                    return objId
                elif 'listContents' in contents:
                    stream.defineList(objId, [transform(x) for x in contents['listContents']])
                    return objId
                else:
                    assert 'contentsAsNumpyArray' in contents
                    contentsAsNumpy = contents['contentsAsNumpyArray']

                    stream.definePackedHomogenousData(
                        objId,
                        TypeDescription.PackedHomogenousData(
                            TypeDescription.dtypeToPrimitive(contentsAsNumpy.dtype),
                            contentsAsNumpy.tostring()
                            )
                        )

                    return objId

            if implval.isTuple():
                stackTraceAsJsonOrNone = self.getStackTraceAsJsonOrNone(implval)
                if stackTraceAsJsonOrNone is not None:
                    stream.defineStacktrace(objId, stackTraceAsJsonOrNone)
                    return objId
                else:
                    assert False, "unknown tuple, but not a stacktra"

            if implval.isObject():
                objectClass = implval.getObjectClass()

                if objectClass == self.pyforaBoundMethodClass:
                    nameAsImplval = implval.getObjectLexicalMember("@name")[0]
                    if not nameAsImplval.isSymbol():
                        raise pyfora.ForaToPythonConversionError(
                            "PyBoundMethod found with name %s of type %s, which should be a symbol but is not."
                                % (nameAsImplval, nameAsImplval.type)
                            )

                    stream.defineInstanceMethod(
                        objId,
                        transform(implval.getObjectLexicalMember("@self")[0]),
                        nameAsImplval.pyval[1:]
                        )
                    return objId

                defPoint = implval.getObjectDefinitionPoint()
                if defPoint is not None:
                    if objectClass is not None:
                        classObjectId = transform(objectClass)
                        members = {}

                        for memberName in objectClass.objectMembers:
                            if memberName is not None:
                                member = implval.getObjectLexicalMember(memberName)
                                if member is not None and member[1] is None:
                                    assert memberName == "@m"
                                    assert member[0].isTuple()

                                    membersTuple = member[0]
                                    memberNames = membersTuple.getTupleNames()
                                    for i, name in enumerate(memberNames):
                                        result = transform(membersTuple[i])

                                        if result is not UnconvertibleToken:
                                            members[str(name)] = transform(membersTuple[i])

                        stream.defineClassInstance(objId, classObjectId, members)

                        return objId
                    else:
                        members = {}
                        lexicalMembers = implval.objectLexicalMembers
                        for memberAndBindingSequence in lexicalMembers.iteritems():
                            #if the binding sequence is empty, then this binding refers to 'self'
                            if isinstance(memberAndBindingSequence[1], ForaNative.ImplValContainer) or memberAndBindingSequence[1][0]:
                                memberName = memberAndBindingSequence[0]
                                member = implval.getObjectLexicalMember(memberName)
                                if member is not None and member[1] is None:
                                    if member[0] != Symbol_uninitialized:
                                        transformed = transform(member[0])

                                        if transformed is not UnconvertibleToken:
                                            members[str(memberName)] = transformed

                        om = implval.objectMetadata
                        if 'classMetadata' in om:
                            om = om['classMetadata']
                        om = om['sourceText'].objectMetadata

                        sourceFileId = transformFile(defPoint.defPoint.asExternal.paths[0], om.pyval)

                        stream.defineFunction(
                            objId,
                            sourceFileId,
                            defPoint.range.start.line,
                            members
                            )

                        return objId

            elif implval.isClass():
                members = {}
                defPoint = implval.getObjectDefinitionPoint()

                lexicalMembers = implval.objectLexicalMembers
                for memberAndBindingSequence in lexicalMembers.iteritems():
                    #if the binding sequence is empty, then this binding refers to 'self'
                    if isinstance(memberAndBindingSequence[1], ForaNative.ImplValContainer) or memberAndBindingSequence[1][0]:
                        memberName = memberAndBindingSequence[0]
                        member = implval.getObjectLexicalMember(memberName)
                        if member is not None and member[1] is None:
                            result = transform(member[0])
                            if result is not UnconvertibleToken:
                                members[str(memberName)] = result

                sourcePath = defPoint.defPoint.asExternal.paths[0]

                om = implval.objectMetadata
                if 'classMetadata' in om:
                    om = om['classMetadata']
                om = om['sourceText'].objectMetadata

                sourceFileId = transformFile(defPoint.defPoint.asExternal.paths[0], om.pyval)
                
                stream.defineClass( 
                    objId,
                    sourceFileId,
                    defPoint.range.start.line,
                    members,
                    #this is a little wrong. When going python->binary, we would have
                    #a list of base classes. When going pyfora->binary, we're holding the
                    #base classes by name as free variables.
                    []
                    )
                return objId

            logging.error("Failed to convert %s of type %s back to python", implval, str(implval.type))

            raise pyfora.ForaToPythonConversionError(
                "Result cannot be translated back to python."
                )


        root_id = transform(implval)

        stream.defineEndOfStream()

        return root_id, anyNeedLoading[0]

    def getStackTraceAsJsonOrNone(self, implval):
        tup = implval.getTuple()

        if len(tup) != 2:
            return None

        return self.exceptionCodeLocationsAsJson(tup)

    def exceptionCodeLocationsAsJson(self, stacktraceAndVarsInScope):
        hashes = stacktraceAndVarsInScope[0].getStackTrace()

        if hashes is None:
            return None

        codeLocations = [ForaNative.getCodeLocation(h) for h in hashes]
        codeLocations = [c for c in codeLocations if c is not None]

        def formatCodeLocation(c):
            if not c.defPoint.isExternal():
                return None
            def posToJson(simpleParsePosition):
                return {
                    'characterOffset': simpleParsePosition.rawOffset,
                    'line': simpleParsePosition.line,
                    'col': simpleParsePosition.col
                    }
            return {
                'path': list(c.defPoint.asExternal.paths),
                'range': {
                    'start': posToJson(c.range.start),
                    'stop': posToJson(c.range.stop)
                    }
                }

        return tuple(
                x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None
                )


canonicalPurePythonModuleCache_ = [None]
def canonicalPurePythonModule():
    if canonicalPurePythonModuleCache_[0] is None:
        path = os.path.join(os.path.abspath(os.path.split(pyfora.__file__)[0]), "fora")
        moduleTree = ModuleDirectoryStructure.ModuleDirectoryStructure.read(path, "purePython", "fora")
        
        canonicalPurePythonModuleCache_[0] = ModuleImporter.importModuleFromMDS(
            moduleTree,
            "fora",
            "purePython",
            searchForFreeVariables=True
            )

    return canonicalPurePythonModuleCache_[0]


def constructConverter(purePythonModuleImplval, vdm):
    if purePythonModuleImplval is None:
        return Converter(vdmOverride=vdm)
    else:
        singletonAndExceptionConverter = \
            PyforaSingletonAndExceptionConverter.PyforaSingletonAndExceptionConverter(
                purePythonModuleImplval
                )

        primitiveTypeMapping = {
            bool: purePythonModuleImplval.getObjectMember("PyBool"),
            str: purePythonModuleImplval.getObjectMember("PyString"),
            int: purePythonModuleImplval.getObjectMember("PyInt"),
            float: purePythonModuleImplval.getObjectMember("PyFloat"),
            type(None): purePythonModuleImplval.getObjectMember("PyNone"),
            }


        nativeConstantConverter = ForaNative.PythonConstantConverter(
            primitiveTypeMapping
            )

        nativeListConverter = ForaNative.makePythonListConverter(
            purePythonModuleImplval.getObjectMember("PyList")
            )

        nativeTupleConverter = ForaNative.makePythonTupleConverter(
            purePythonModuleImplval.getObjectMember("PyTuple")
            )

        nativeDictConverter = ForaNative.makePythonDictConverter(
            purePythonModuleImplval.getObjectMember("PyDict")
            )

        foraBuiltinsImplVal = ModuleImporter.builtinModuleImplVal()

        return Converter(
            nativeListConverter=nativeListConverter,
            nativeTupleConverter=nativeTupleConverter,
            nativeDictConverter=nativeDictConverter,
            nativeConstantConverter=nativeConstantConverter,
            singletonAndExceptionConverter=singletonAndExceptionConverter,
            vdmOverride=vdm,
            purePythonModuleImplVal=purePythonModuleImplval,
            foraBuiltinsImplVal=foraBuiltinsImplVal
            )

