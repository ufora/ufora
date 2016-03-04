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

import ufora.FORA.python.Expression as Expression
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter
import ufora.FORA.python.PurePython.ConstantConverter as ConstantConverter
import ufora.FORA.python.ForaValue as ForaValue
import ufora.BackendGateway.ComputedValue.ComputedValue as ComputedValue

import pyfora.TypeDescription as TypeDescription
import pyfora.StronglyConnectedComponents as StronglyConnectedComponents
import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora

import ast
import logging

import ufora.native.FORA as ForaNative


emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])
empytObjectExpression = ForaNative.parseStringToExpression(
    "object {}",
    emptyCodeDefinitionPoint,
    ""
    )
Symbol_CreateInstance = ForaNative.makeSymbol("CreateInstance")
Symbol_Call = ForaNative.makeSymbol("Call")
Symbol_uninitialized = ForaNative.makeSymbol("PyforaUninitializedVariable")
Symbol_invalid = ForaNative.makeSymbol("PyforaInvalidVariable")
Symbol_unconvertible = ForaNative.makeSymbol("PyforaUnconvertibleValue")



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
                 foraBuiltinsImplVal=None):
        self.convertedValues = {}

        self.boundExpressions = {}

        self.constantConverter = ConstantConverter.ConstantConverter(
            nativeConstantConverter=nativeConstantConverter
            )

        self.singletonAndExceptionConverter = singletonAndExceptionConverter

        self.nativeListConverter = nativeListConverter

        self.nativeTupleConverter = nativeTupleConverter

        self.nativeDictConverter = nativeDictConverter

        self.vdm_ = vdmOverride

        self.pyforaBoundMethodClass = purePythonModuleImplVal.getObjectMember("PyBoundMethod")

        builtinMemberMapping = Converter.computeBuiltinMemberMapping(
            purePythonModuleImplVal=purePythonModuleImplVal,
            foraBuiltinsImplVal=foraBuiltinsImplVal
            )

        self.nativeConverter = ForaNative.makePythonAstConverter(
            nativeConstantConverter,
            self.nativeListConverter,
            self.nativeTupleConverter,
            self.nativeDictConverter,
            purePythonModuleImplVal,
            builtinMemberMapping
            )

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
            dependencyGraph = objectRegistry.computeDependencyGraph(objectId)
            objectIdToObjectDefinition = {
                objId: objectRegistry.getDefinition(objId)
                for objId in dependencyGraph.iterkeys()
                }
            convertedValue = self._convert(objectId, dependencyGraph, objectIdToObjectDefinition)
            self.convertedValues[objectId] = convertedValue
            callback(convertedValue)
        except pyfora.PythonToForaConversionError as e:
            callback(e)

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
            return self.convertUnconvertibleValue(objectId)
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

        return self.nativeDictConverter.createDict(convertedKeysAndVals)

    def convertUnconvertibleValue(self, objectId):
        # uh, yeah ... this guy probably needs a better name. Sorry.

        tr = Symbol_unconvertible
        self.convertedValues[objectId] = tr
        return tr

    def convertPrimitive(self, value):
        if isinstance(value, list):
            return self.nativeListConverter.createListOfPrimitives(
                value,
                self.constantConverter.nativeConstantConverter,
                self.vdm_
                )

        return self.constantConverter.convert(value)

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

    def convertList(self, listId, dependencyGraph, objectIdToObjectDefinition):
        self._convertListMembers(listId, dependencyGraph, objectIdToObjectDefinition)
        memberIds = objectIdToObjectDefinition[listId].memberIds

        return self.nativeListConverter.createList(
            [self.convertedValues[memberId] for memberId in memberIds],
            self.vdm_
            )

    def convertTuple(self, tupleId, dependencyGraph, objectIdToObjectDefinition):
        self._convertListMembers(tupleId, dependencyGraph, objectIdToObjectDefinition)
        memberIds = objectIdToObjectDefinition[tupleId].memberIds

        return self.nativeTupleConverter.createTuple(
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

    def convertStronglyConnectedComponentWithMoreThanOneNode(self,
                                                             objectIdToObjectDefinition,
                                                             stronglyConnectedComponent):
        (createObjectExpression, memberToObjectIdMap) = \
            self.getCreateObjectExpressionAndMemberToObjectIdMap(
                objectIdToObjectDefinition,
                stronglyConnectedComponent
                )

        objectImplVal = self.bindDependentValuesToCreateObjectExpression(
            createObjectExpression,
            memberToObjectIdMap,
            objectIdToObjectDefinition
            )

        self.registerObjectMembers(
            objectImplVal,
            memberToObjectIdMap
            )

    def getCreateObjectExpressionAndMemberToObjectIdMap(self,
                                                        objectIdToObjectDefinition,
                                                        stronglyConnectedComponent):
        naiveConvertedFunctions = dict()
        for objectId in stronglyConnectedComponent:
            objectDefinition = objectIdToObjectDefinition[objectId]

            if isinstance(objectDefinition, TypeDescription.ClassInstanceDescription):
                classDesc = objectIdToObjectDefinition[objectDefinition.classId]
                sourceFile = objectIdToObjectDefinition[classDesc.sourceFileId]
                lineNumber = classDesc.lineNumber
                raise pyfora.PythonToForaConversionError(
                    "Classes and instances cannot be mutually recursive",
                    trace=[{'path': sourceFile.path, 'line': lineNumber}]
                    )

            assert isinstance(
                objectDefinition,
                (TypeDescription.FunctionDefinition,
                 TypeDescription.ClassDefinition)), type(objectDefinition)

            naiveConvertedFunctions[objectId] = \
                self.convertPyClassOrFunctionDefinitionToForaFunctionExpression(
                    objectDefinition,
                    objectIdToObjectDefinition
                    )
        # at this point, naiveConvertedFunctions is a map: objectId -> functionExpr

        # renamedObjectMapping is a map: objectId -> varname,
        # where varname is (essentially) just the hash of the corresponding functionExpr
        renamedObjectMapping = self.computeRenamedObjectMapping(
            naiveConvertedFunctions
            )

        # replace the known free var chains in the strongly connected component
        # with the varnames coming from the renamedObjectMapping
        convertedFunctions = self.replaceKnownMemberChainsWithRenamedVariables(
            naiveConvertedFunctions,
            renamedObjectMapping,
            objectIdToObjectDefinition,
            stronglyConnectedComponent
            )

        createObjectExpression = empytObjectExpression

        for objectId, varname in sorted(renamedObjectMapping.items(), key=lambda p: p[1]):
            createObjectExpression = ForaNative.prependMemberToCreateObjectExpression(
                createObjectExpression,
                varname,
                convertedFunctions[objectId]
                )

        return createObjectExpression, renamedObjectMapping

    def registerObjectMembers(self, objectImplVal, renamedObjectMapping):
        for objectId, memberName in renamedObjectMapping.iteritems():
            memberImplValOrNone = objectImplVal.getObjectMember(memberName)

            if memberImplValOrNone is None:
                raise pyfora.PythonToForaConversionError(
                    ("An internal error occurred: " +
                     "getObjectMember unexpectedly returned None")
                    )

            self.convertedValues[objectId] = memberImplValOrNone

    def bindDependentValuesToCreateObjectExpression(self,
                                                    createObjectExpression,
                                                    renamedObjectMapping,
                                                    objectIdToObjectDefinition):
        stronglyConnectedComponent = renamedObjectMapping.keys()

        renamedVariableMapping = dict()

        for objectId in stronglyConnectedComponent:
            for freeVariableMemberAccessChain, dependentId in \
                objectIdToObjectDefinition[objectId].freeVariableMemberAccessChainsToId.iteritems():
                if dependentId not in stronglyConnectedComponent:
                    renamedVariableMapping[freeVariableMemberAccessChain] = \
                        self.convertedValues[dependentId]

        return self.specializeFreeVariableMemberAccessChainsAndEvaluate(
            createObjectExpression,
            renamedVariableMapping
            )

    def replaceKnownMemberChainsWithRenamedVariables(self,
                                                     objectIdToForaFunctionExpression,
                                                     renamedVariableMapping,
                                                     objectIdToObjectDefinition,
                                                     stronglyConnectedComponent):
        """
        Given a strongly connected component of functions, and a renamed object mapping
        replace known free variable access chains in the function expressions with the
        renamed variables
        """
        tr = dict()
        for objectId in stronglyConnectedComponent:
            objectDefinition = objectIdToObjectDefinition[objectId]
            foraFunctionExpression = objectIdToForaFunctionExpression[objectId]

            transformedFunction = foraFunctionExpression
            for freeVariableMemberAccessChain, dependentObjectId in \
                objectDefinition.freeVariableMemberAccessChainsToId.iteritems():
                if dependentObjectId in stronglyConnectedComponent:
                    transformedFunction = transformedFunction.rebindFreeVariableMemberAccessChain(
                        tuple(freeVariableMemberAccessChain.split('.')),
                        renamedVariableMapping[dependentObjectId]
                        )

            tr[objectId] = transformedFunction

        return tr

    def computeRenamedObjectMapping(self, objectIdToForaFunctionExpression):
        """
        Given a map: objectId -> functionExpression,
        return a map: objectId -> varName
        where each varName is essentially the hash of the corresponding functionExpression
        """
        renamedObjectMapping = dict()

        mentionedVariables = set()

        for objectId, foraFunctionExpression in objectIdToForaFunctionExpression.iteritems():
            mentionedVariables.update(foraFunctionExpression.mentionedVariables)
            renamedObjectMapping[objectId] = Expression.freshVarname(
                "_%s_" % foraFunctionExpression.hash(),
                mentionedVariables
                )

        return renamedObjectMapping

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
            self.convertedValues[objectId] = Symbol_unconvertible

        else:
            assert False, "haven't gotten to this yet %s" % type(objectDefinition)

    def convertInstanceMethod(self, objectId, objectIdToObjectDefinition):
        objectDef = objectIdToObjectDefinition[objectId]
        instance = self.convertedValues[objectDef.instanceId]
        bound = instance.getObjectMember(objectDef.methodName)
        assert bound is not None
        return bound

    def convertWithBlock(self, objectId, withBlockDescription, objectIdToObjectDefinition):
        foraFunctionExpression = self.getFunctionExpressionFromWithBlockDescription(
            withBlockDescription,
            objectIdToObjectDefinition
            )

        renamedVariableMapping = {}

        for freeVariableMemberAccessChain, dependentId in \
            withBlockDescription.freeVariableMemberAccessChainsToId.iteritems():
            renamedVariableMapping[freeVariableMemberAccessChain] = \
                self.convertedValues[dependentId]

        tr = self.specializeFreeVariableMemberAccessChainsAndEvaluate(
            foraFunctionExpression,
            renamedVariableMapping
            )

        self.convertedValues[objectId] = tr

        return tr

    def getFunctionExpressionFromWithBlockDescription(self,
                                                      withBlockDescription,
                                                      objectIdToObjectDefinition):
        nativeWithBodyAst = self._getNativePythonFunctionDefFromWithBlockDescription(
            withBlockDescription,
            objectIdToObjectDefinition
            )

        sourcePath = objectIdToObjectDefinition[withBlockDescription.sourceFileId].path

        foraFunctionExpression = \
            self.nativeConverter.convertPythonAstWithBlockFunctionDefToForaOrParseError(
                nativeWithBodyAst.asFunctionDef,
                nativeWithBodyAst.extent,
                ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                [x.split(".")[0] for x in withBlockDescription.freeVariableMemberAccessChainsToId]
                )

        if isinstance(foraFunctionExpression, ForaNative.PythonToForaConversionError):
            raise convertNativePythonToForaConversionError(
                foraFunctionExpression,
                objectIdToObjectDefinition[withBlockDescription.sourceFileId].path
                )

        return foraFunctionExpression

    def _getNativePythonFunctionDefFromWithBlockDescription(self,
                                                            withBlockDescription,
                                                            objectIdToObjectDefinition):
        sourceText = objectIdToObjectDefinition[withBlockDescription.sourceFileId].text
        sourceLineOffsets = PythonAstConverter.computeLineOffsets(sourceText)
        sourceTree = ast.parse(sourceText)
        withTree = PyAstUtil.withBlockAtLineNumber(
            sourceTree,
            withBlockDescription.lineNumber
            )

        withBodyAsFunctionAst = ast.FunctionDef(
            name="__withBodyFunction",
            lineno=withTree.lineno,
            col_offset=withTree.col_offset,
            args=ast.arguments(
                args=[],
                vararg=None,
                kwarg=None,
                defaults=[]),
            body=withTree.body,
            decorator_list=[]
            )

        nativeWithBodyAst = PythonAstConverter.convertPythonAstToForaPythonAst(
            withBodyAsFunctionAst,
            sourceLineOffsets
            )

        return nativeWithBodyAst

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
        classMemberNameToImplVal = {
            classMemberName: self.convertedValues[memberId]
            for classMemberName, memberId in
            classInstanceDescription.classMemberNameToClassMemberId.iteritems()
            }
        classImplVal = self.convertedValues[classInstanceDescription.classId]

        memberNames = tuple(sorted(name for name in classMemberNameToImplVal.iterkeys()))
        memberValues = tuple(classMemberNameToImplVal[name] for name in memberNames)
        convertedValueOrNone = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                (classImplVal,
                 Symbol_CreateInstance,
                 ForaNative.CreateNamedTuple(memberValues, memberNames))
                )
            )

        if convertedValueOrNone is None:
            raise pyfora.PythonToForaConversionError(
                ("An internal error occurred: " +
                 "function stage 1 simulation unexpectedly returned None")
                )

        self.convertedValues[objectId] = convertedValueOrNone

    def convertStronglyConnectedComponentWithOneFunctionOrClass(self,
                                                                objectId,
                                                                classOrFunctionDefinition,
                                                                objectIdToObjectDefinition):
        foraExpression = self.convertPyClassOrFunctionDefinitionToForaFunctionExpression(
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            )

        renamedVariableMapping = {}

        for freeVariableMemberAccessChain, dependentId in \
            classOrFunctionDefinition.freeVariableMemberAccessChainsToId.iteritems():
            renamedVariableMapping[freeVariableMemberAccessChain] = \
                self.convertedValues[dependentId]

        if isinstance(classOrFunctionDefinition, TypeDescription.ClassDefinition):
            for i, baseId in enumerate(classOrFunctionDefinition.baseClassIds):
                renamedVariableMapping["baseClass%d" % i] = self.convertedValues[baseId]

        self.convertedValues[objectId] = \
            self.specializeFreeVariableMemberAccessChainsAndEvaluate(
                foraExpression,
                renamedVariableMapping
                )

    def specializeFreeVariableMemberAccessChainsAndEvaluate(self,
                                                            foraExpression,
                                                            renamedVariableMapping):
        foraExpression, renamedVariableMapping = \
            self.reduceFreeVariableMemberAccessChains(
                foraExpression,
                renamedVariableMapping
                )

        foraExpression = self.handleUnconvertibleValuesInExpression(
            foraExpression,
            renamedVariableMapping
            )

        return self.specializeFreeVariablesAndEvaluate(
            foraExpression,
            renamedVariableMapping
            )

    def handleUnconvertibleValuesInExpression(
            self,
            foraExpression,
            renamedVariableMapping
            ):
        unconvertibles = [
            k for k, v in renamedVariableMapping.iteritems() \
            if v == Symbol_unconvertible
            ]

        foraExpression = self.nativeConverter.replaceUnconvertiblesWithThrowExprs(
            foraExpression,
            unconvertibles
            )

        return foraExpression

    def specializeFreeVariablesAndEvaluate(
            self,
            foraExpression,
            renamedVariableMapping
            ):
        allAreIVC = True
        for _, v in renamedVariableMapping.iteritems():
            if not isinstance(v, ForaNative.ImplValContainer):
                allAreIVC = False

        if allAreIVC:
            missingVariableDefinitions = [
                x for x in foraExpression.freeVariables if x not in renamedVariableMapping
                ]

            if missingVariableDefinitions:
                raise pyfora.PythonToForaConversionError(
                    ("An internal error occurred: we didn't provide a " +
                     "definition for the following variables: %s" % missingVariableDefinitions +
                     ". Most likely, there is a mismatch between our analysis of the "
                     "python code and the generated FORA code underneath. Please file a bug report."
                    ))

            #we need to determine whether we should bind the free variables in this expression as constants
            #inline in the code, or as class members. Binding them as constants speeds up the compiler,
            #but if we have the same function bound repeatedly with many constants, we'll end up
            #producing far too much code. This algorithm binds as constants the _First_ time we bind
            #a given expression with given arguments, and as members any future set of times. This
            #should cause it to bind modules and classes that don't have any data flowing through them
            #as constants, and closures and functions we're calling repeatedly using class members.
            shouldMapArgsAsConstants = True

            boundValues = tuple(renamedVariableMapping[k].hash for k in sorted(renamedVariableMapping))
            if foraExpression.hash() not in self.boundExpressions:
                self.boundExpressions[foraExpression.hash()] = boundValues
            else:
                bound = self.boundExpressions[foraExpression.hash()]
                if boundValues != bound:
                    shouldMapArgsAsConstants = False

            return ForaNative.evaluateRootLevelCreateObjectExpression(
                foraExpression,
                renamedVariableMapping,
                shouldMapArgsAsConstants
                )
        else:
            #function that evaluates the CreateObject.
            #Args are the free variables, in lexical order
            expressionAsIVC = foraExpression.toFunctionImplval(False)

            args = []
            for f in foraExpression.freeVariables:
                args.append(renamedVariableMapping[f])

            res = ComputedValue.ComputedValue(
                args=(expressionAsIVC, Symbol_Call) + tuple(args)
                )

            return res

    def reduceFreeVariableMemberAccessChains(self,
                                             expr,
                                             freeVariableMemberAccessChainToImplValMap):
        """
        given an expression `expr` and mapping
        `freeVariableMemberAccessChainToImplValMap`,
        replace the occurences of the keys of the mapping in expr
        with fresh variable names.

        Returns the new expression, and a mapping from the replacing
        variables to their corresponding (implval) values.
        """
        renamedVariableMapping = {}
        for chain, implval in freeVariableMemberAccessChainToImplValMap.iteritems():
            assert isinstance(chain, str)
            chain = chain.split('.')

            if len(chain) == 1:
                renamedVariableMapping[chain[0]] = implval
            else:
                newName = Expression.freshVarname(
                    '_'.join(chain),
                    set(expr.mentionedVariables)
                    )
                renamedVariableMapping[newName] = implval
                expr = expr.rebindFreeVariableMemberAccessChain(
                    chain,
                    newName
                    )

        return expr, renamedVariableMapping


    def convertPyClassOrFunctionDefinitionToForaFunctionExpression(self,
                                                                   classOrFunctionDefinition,
                                                                   objectIdToObjectDefinition):
        pyAst = self.convertClassOrFunctionDefinitionToNativePyAst(
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            )

        assert pyAst is not None

        sourcePath = objectIdToObjectDefinition[classOrFunctionDefinition.sourceFileId].path

        tr = None
        if isinstance(classOrFunctionDefinition, TypeDescription.FunctionDefinition):
            if isinstance(pyAst, ForaNative.PythonAstStatement) and pyAst.isFunctionDef():
                tr = self.nativeConverter.convertPythonAstFunctionDefToForaOrParseError(
                    pyAst.asFunctionDef,
                    pyAst.extent,
                    ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath])
                    )
            else:
                assert pyAst.isLambda()
                tr = self.nativeConverter.convertPythonAstLambdaToForaOrParseError(
                    pyAst.asLambda,
                    pyAst.extent,
                    ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath])
                    )

        elif isinstance(classOrFunctionDefinition, TypeDescription.ClassDefinition):
            objectIdToFreeVar = {
                v: k
                for k, v in classOrFunctionDefinition.freeVariableMemberAccessChainsToId.iteritems()
                }
            baseClasses = [
                objectIdToFreeVar[baseId].split('.')
                for baseId in classOrFunctionDefinition.baseClassIds
                ]
            tr = self.nativeConverter.convertPythonAstClassDefToForaOrParseError(
                pyAst.asClassDef,
                pyAst.extent,
                ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                baseClasses
                )

        else:
            assert False

        if isinstance(tr, ForaNative.PythonToForaConversionError):
            raise convertNativePythonToForaConversionError(
                tr,
                sourcePath
                )

        return tr

    def convertClassOrFunctionDefinitionToNativePyAst(self,
                                                      classOrFunctionDefinition,
                                                      objectIdToObjectDefinition):
        sourceText = objectIdToObjectDefinition[classOrFunctionDefinition.sourceFileId].text

        pyAst = PythonAstConverter.parseStringToPythonAst(sourceText)

        assert pyAst is not None

        pyAst = pyAst.functionClassOrLambdaDefAtLine(classOrFunctionDefinition.lineNumber)

        assert pyAst is not None, (sourceText, classOrFunctionDefinition.lineNumber)

        return pyAst

    def unwrapPyforaDictToDictOfAssignedVars(self, dictIVC):
        """Take a Pyfora dictionary, and return a dict {string->IVC}. Returns None if not possible."""
        pyforaDict = self.nativeDictConverter.invertDict(dictIVC)
        if pyforaDict is None:
            return None

        res = {}

        for pyforaKey, pyforaValue in pyforaDict.iteritems():
            if pyforaValue != Symbol_uninitialized and pyforaValue != Symbol_invalid:
                maybePyforaKeyString = self.constantConverter.invertForaConstant(pyforaKey)
                if isinstance(maybePyforaKeyString, tuple) and isinstance(maybePyforaKeyString[0], str):
                    res[maybePyforaKeyString[0]] = pyforaValue
                else:
                    return None

        return res

    def unwrapPyforaTupleToTuple(self, tupleIVC):
        pyforaTuple = self.nativeTupleConverter.invertTuple(tupleIVC)
        if pyforaTuple is None:
            return None

        res = tuple([pyforaValue for pyforaValue in pyforaTuple])
        return res

    def transformPyforaImplval(self, implval, transformer, vectorContentsExtractor):
        """Walk an implval that represents a pyfora value and unwrap it, passing data to the transformer.

        implval - the pyfora value we want to visit
        transformer - an instance of PyforaToJsonTransformer that receives data and builds the relevant
            representation that we will return.
        """
        value = self.constantConverter.invertForaConstant(implval)
        if value is not None:
            if isinstance(value, tuple):
                #this is a simple constant
                return transformer.transformPrimitive(value[0])
            else:
                #this is a vector
                assert isinstance(value, ForaNative.ImplValContainer)

                if len(value) == 0:
                    return transformer.transformPrimitive("")

                assert value.isVectorOfChar()

                contents = vectorContentsExtractor(value)

                if contents is None:
                    return transformer.transformStringThatNeedsLoading(len(value))
                else:
                    assert 'string' in contents
                    return transformer.transformPrimitive(contents['string'])

        if self.singletonAndExceptionConverter is not None:
            value = self.singletonAndExceptionConverter.convertInstanceToSingletonName(implval)
            if value is not None:
                return transformer.transformSingleton(value)

            value = self.singletonAndExceptionConverter.convertExceptionInstance(implval)
            if value is not None:
                return transformer.transformBuiltinException(
                    value[0],
                    self.transformPyforaImplval(value[1], transformer, vectorContentsExtractor)
                    )

            value = self.singletonAndExceptionConverter.convertPyAbortExceptionInstance(
                implval
                )
            if value is not None:
                return transformer.transformPyAbortException(
                    value[0],
                    self.transformPyforaImplval(value[1], transformer, vectorContentsExtractor)
                    )

        value = self.nativeTupleConverter.invertTuple(implval)
        if value is not None:
            return transformer.transformTuple([
                self.transformPyforaImplval(x, transformer, vectorContentsExtractor)
                for x in value
                ])

        value = self.nativeDictConverter.invertDict(implval)
        if value is not None:
            return transformer.transformDict(
                keys=[
                    self.transformPyforaImplval(k, transformer, vectorContentsExtractor)
                    for k in value.keys()
                    ],
                values=[
                    self.transformPyforaImplval(v, transformer, vectorContentsExtractor)
                    for v in value.values()
                    ]
                )

        listItemsAsVector = self.nativeListConverter.invertList(implval)
        if listItemsAsVector is not None:
            contents = vectorContentsExtractor(listItemsAsVector)

            if contents is None:
                return transformer.transformListThatNeedsLoading(len(listItemsAsVector))
            elif 'listContents' in contents:
                return transformer.transformList(
                    [self.transformPyforaImplval(x, transformer, vectorContentsExtractor)
                     for x in contents['listContents']]
                    )
            else:
                assert 'firstElement' in contents
                firstElement = contents['firstElement']
                contentsAsNumpy = contents['contentsAsNumpyArrays']

                return transformer.transformHomogenousList(
                    self.transformPyforaImplval(firstElement, transformer, vectorContentsExtractor),
                    contentsAsNumpy
                    )

        if implval.isTuple():
            stackTraceAsJsonOrNone = self.getStackTraceAsJsonOrNone(implval)
            if stackTraceAsJsonOrNone is not None:
                return stackTraceAsJsonOrNone

        if implval.isObject():
            objectClass = implval.getObjectClass()

            if objectClass == self.pyforaBoundMethodClass:
                nameAsImplval = implval.getObjectLexicalMember("@name")[0]
                if not nameAsImplval.isSymbol():
                    raise pyfora.ForaToPythonConversionError(
                        "PyBoundMethod found with name %s of type %s, which should be a symbol but is not."
                            % (nameAsImplval, nameAsImplval.type)
                        )

                return transformer.transformBoundMethod(
                    self.transformPyforaImplval(
                        implval.getObjectLexicalMember("@self")[0],
                        transformer,
                        vectorContentsExtractor
                        ),
                    nameAsImplval.pyval[1:]
                    )


            defPoint = implval.getObjectDefinitionPoint()
            if defPoint is not None:
                if objectClass is not None:
                    classObject = self.transformPyforaImplval(objectClass,
                                                              transformer,
                                                              vectorContentsExtractor)
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
                                    members[str(name)] = self.transformPyforaImplval(
                                        membersTuple[i],
                                        transformer,
                                        vectorContentsExtractor
                                        )

                    return transformer.transformClassInstance(classObject, members)
                else:
                    members = {}
                    lexicalMembers = implval.objectLexicalMembers
                    for memberAndBindingSequence in lexicalMembers.iteritems():
                        #if the binding sequence is empty, then this binding refers to 'self'
                        if isinstance(memberAndBindingSequence[1], ForaNative.ImplValContainer) or memberAndBindingSequence[1][0]:
                            memberName = memberAndBindingSequence[0]
                            member = implval.getObjectLexicalMember(memberName)
                            if member is not None and member[1] is None:
                                members[str(memberName)] = self.transformPyforaImplval(
                                    member[0],
                                    transformer,
                                    vectorContentsExtractor
                                    )

                    return transformer.transformFunctionInstance(
                        defPoint.defPoint.asExternal.paths[0],
                        defPoint.range.start.line,
                        members
                        )

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
                        members[str(memberName)] = self.transformPyforaImplval(
                            member[0],
                            transformer,
                            vectorContentsExtractor
                            )

            return transformer.transformClassObject(defPoint.defPoint.asExternal.paths[0],
                                                    defPoint.range.start.line,
                                                    members)

        logging.error("Failed to convert %s of type %s back to python", implval, str(implval.type))

        raise pyfora.ForaToPythonConversionError(
            "Result cannot be translated back to python."
            )

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

        return {
            'stacktrace': [
                x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None
                ]
            }
