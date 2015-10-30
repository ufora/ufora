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
import pyfora.PyAstUtil as PyAstUtil
import pyfora.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora

import ast

import ufora.native.FORA as ForaNative

emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])
empytObjectExpression = ForaNative.parseStringToExpression(
    "object {}",
    emptyCodeDefinitionPoint,
    ""
    )
createInstanceImplVal = ForaNative.makeSymbol("CreateInstance")
callImplVal = ForaNative.makeSymbol("Call")
Symbol_uninitialized = ForaNative.makeSymbol("@uninitialized")

class Converter(object):
    def __init__(self,
                 nativeConstantConverter=None,
                 nativeListConverter=None,
                 nativeTupleConverter=None,
                 nativeDictConverter=None,
                 singletonAndExceptionConverter=None,
                 vdmOverride=None,
                 purePythonModuleImplVal=None
                 ):
        self.convertedValues = {}

        self.constantConverter = ConstantConverter.ConstantConverter(
            nativeConstantConverter=nativeConstantConverter
            )

        self.singletonAndExceptionConverter = singletonAndExceptionConverter

        self.nativeConstantConverter = \
            self.constantConverter.nativeConstantConverter

        self.nativeListConverter = nativeListConverter

        self.nativeTupleConverter = nativeTupleConverter

        if nativeDictConverter is None:
            nativeDictConverter = ForaNative.makeDirectPythonDictConverter()
        self.nativeDictConverter = nativeDictConverter

        self.vdm_ = vdmOverride

        self.purePythonModuleImplVal = purePythonModuleImplVal

        if purePythonModuleImplVal is None:
            self.pyObjectMixinBaseIVC = ForaNative.ImplValContainer()
        else:
            self.pyObjectMixinBaseIVC = purePythonModuleImplVal.getObjectMember("PyObjectBase")

        if purePythonModuleImplVal is None:
            self.pyObjectGeneratorFactoryIVC = ForaNative.makeSymbol("ConvertYieldToIter")
        else:
            self.pyObjectGeneratorFactoryIVC = purePythonModuleImplVal.getObjectMember("CreateGeneratorFromYield")

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

        if isinstance(objectDefinition, TypeDescription.Primitive):
            return self.convertPrimitive(objectDefinition.value)
        elif isinstance(objectDefinition, TypeDescription.RemotePythonObject):
            return self.convertRemotePythonObject(objectDefinition)
        elif isinstance(objectDefinition, TypeDescription.NamedSingleton):
            return self.convertNamedSingleton(objectDefinition)
        elif isinstance(objectDefinition, TypeDescription.BuiltinExceptionInstance):
            return self.convertBuiltinExceptionInstance(
                objectId,
                objectDefinition,
                dependencyGraph,
                objectIdToObjectDefinition
                )
        elif isinstance(objectDefinition,
                        (TypeDescription.FunctionDefinition,
                         TypeDescription.ClassDefinition,
                         TypeDescription.ClassInstanceDescription)
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
        else:
            raise pyfora.PythonToForaConversionError(
                "don't know how to convert %s of type %s" % (
                    objectDefinition, type(objectDefinition)
                    )
                )

    def convertNamedSingleton(self, objectDefinition):
        singleton = self.singletonAndExceptionConverter.convertSingletonByName(
            objectDefinition.singletonName
            )

        if singleton is None:
            raise pyfora.PythonToForaConversionError("No singleton named %s" % objectDefinition.singletonName)

        return singleton

    def convertBuiltinExceptionInstance(self,
                objectId,
                objectDefinition,
                dependencyGraph,
                objectIdToObjectDefinition
                ):
        args = self.convertedValues[objectDefinition.argId]

        return self.singletonAndExceptionConverter.instantiateException(
            objectDefinition.builtinExceptionTypeName,
            args
            )

    def convertRemotePythonObject(
            self,
            objectDefinition
            ):
        computedValueArg = objectDefinition.computedValueArgument

        if isinstance(computedValueArg, int):
            #then this is an object we've already seen. We can assume it's here,
            #because the only way this can happen is to return an object to the server
            #that we've converted, and then have that object be used again in another
            #computation
            return self.convertedValues[computedValueArg]
        else:
            return computedValueArg

    def convertDict(
            self,
            dictId,
            objectDefinition,
            dependencyGraph,
            objectIdToObjectDefinition
            ):
        self._convertListMembers(
            dictId,
            dependencyGraph,
            objectIdToObjectDefinition
            )

        convertedKeysAndVals = {
            self.convertedValues[keyId]: self.convertedValues[valId] for \
            keyId, valId in \
            zip(objectDefinition.keyIds, objectDefinition.valueIds)
            }

        return self.nativeDictConverter.createDict(convertedKeysAndVals)

    def convertPrimitive(self, value):
        return self.constantConverter.convert(value)

    def _assertContainerDoesNotReferenceItself(
            self,
            containerId,
            dependencyGraph,
            stronglyConnectedComponents
            ):
        assert containerId in stronglyConnectedComponents[-1]

        if len(stronglyConnectedComponents[-1]) > 1 or \
           containerId in dependencyGraph[containerId]:
            raise pyfora.PythonToForaConversionError(
                "don't know how to convert lists or tuples which reference themselves"
                )

    def convertList(
            self,
            listId,
            dependencyGraph,
            objectIdToObjectDefinition
            ):
        self._convertListMembers(
            listId,
            dependencyGraph,
            objectIdToObjectDefinition
            )

        memberIds = objectIdToObjectDefinition[listId].memberIds

        return self.nativeListConverter.createList(
            [self.convertedValues[memberId] for memberId in memberIds],
            self.vdm_
            )

    def convertTuple(
            self,
            tupleId,
            dependencyGraph,
            objectIdToObjectDefinition
            ):
        self._convertListMembers(
            tupleId,
            dependencyGraph,
            objectIdToObjectDefinition
            )

        memberIds = objectIdToObjectDefinition[tupleId].memberIds

        return self.nativeTupleConverter.createTuple(
            [self.convertedValues[memberId] for memberId in memberIds]
            )


    def _convertListMembers(
            self,
            listId,
            dependencyGraph,
            objectIdToObjectDefinition
            ):
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

    def convertObjectWithDependencies(
            self,
            objectId,
            dependencyGraph,
            objectIdToObjectDefinition
            ):
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

    def convertStronglyConnectedComponent(
            self,
            dependencyGraph,
            stronglyConnectedComponent,
            objectIdToObjectDefinition
            ):
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

    def convertStronglyConnectedComponentWithMoreThanOneNode(
            self,
            objectIdToObjectDefinition,
            stronglyConnectedComponent
            ):
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

    def getCreateObjectExpressionAndMemberToObjectIdMap(
            self,
            objectIdToObjectDefinition,
            stronglyConnectedComponent
            ):
        naiveConvertedFunctions = dict()
        for objectId in stronglyConnectedComponent:
            objectDefinition = objectIdToObjectDefinition[objectId]

            assert isinstance(
                objectDefinition, 
                (TypeDescription.FunctionDefinition, 
                 TypeDescription.ClassDefinition)), type(objectDefinition)

            naiveConvertedFunctions[objectId] = \
                self.convertPyClassOrFunctionDefinitionToForaFunctionExpression(
                    objectDefinition,
                    objectIdToObjectDefinition
                    )

        renamedObjectMapping = self.computeRenamedObjectMapping(
            naiveConvertedFunctions
            )

        convertedFunctions = self.transformFunctions(
            naiveConvertedFunctions,
            renamedObjectMapping,
            objectIdToObjectDefinition,
            stronglyConnectedComponent
            )

        createObjectExpression = empytObjectExpression

        for objectId, functionExpression in convertedFunctions.iteritems():
            createObjectExpression = ForaNative.prependMemberToCreateObjectExpression(
                createObjectExpression,
                renamedObjectMapping[objectId],
                functionExpression
                )

        return createObjectExpression, renamedObjectMapping

    def registerObjectMembers(
            self,
            objectImplVal,
            renamedObjectMapping
            ):
        for objectId, memberName in renamedObjectMapping.iteritems():
            memberImplVal = objectImplVal.getObjectMember(memberName)
            self.convertedValues[objectId] = memberImplVal

    def bindDependentValuesToCreateObjectExpression(
            self,
            createObjectExpression,
            renamedObjectMapping,
            objectIdToObjectDefinition
            ):
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

    def transformFunctions(
            self,
            objectIdToForaFunctionExpression,
            objectIdToVarname,
            objectIdToObjectDefinition,
            stronglyConnectedComponent
            ):
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
                        objectIdToVarname[dependentObjectId]
                        )

            tr[objectId] = transformedFunction

        return tr

    def computeRenamedObjectMapping(self, objectIdToForaFunctionExpression):
        renamedObjectMapping = dict()

        mentionedVariables = set()
        for objectId, foraFunctionExpression in objectIdToForaFunctionExpression.iteritems():
            mentionedVariables.update(foraFunctionExpression.mentionedVariables)
            renamedObjectMapping[objectId] = Expression.freshVarname(
                "_%s_" % objectId,
                mentionedVariables
                )

        return renamedObjectMapping

    def convertStronglyConnectedComponentWithOneNode(
            self,
            dependencyGraph,
            stronglyConnectedComponent,
            objectIdToObjectDefinition
            ):
        objectId = stronglyConnectedComponent[0]
        objectDefinition = objectIdToObjectDefinition[objectId]

        if isinstance(objectDefinition, TypeDescription.Primitive):
            self.convertedValues[objectId] = \
                self.convertPrimitive(objectDefinition.value)

        elif isinstance(objectDefinition, (TypeDescription.FunctionDefinition,
                                           TypeDescription.ClassDefinition)):
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
            self.convertedValues[objectId] = \
                self.convertFile(
                    objectDefinition
                    )

        elif isinstance(objectDefinition, TypeDescription.RemotePythonObject):
            self.convertedValues[objectId] = \
                self.convertRemotePythonObject(
                    objectDefinition
                    )

        elif isinstance(objectDefinition, TypeDescription.BuiltinExceptionInstance):
            self.convertedValues[objectId] = \
                self.convertBuiltinExceptionInstance(
                    objectId,
                    objectDefinition,
                    self._computeRestrictedGraph(
                        objectId,
                        dependencyGraph
                        ),
                    objectIdToObjectDefinition
                    )

        elif isinstance(objectDefinition, TypeDescription.NamedSingleton):
            self.convertedValues[objectId] = \
                self.convertNamedSingleton(
                    objectDefinition
                    )

        elif isinstance(objectDefinition, TypeDescription.WithBlockDescription):
            self.convertedValues[objectId] = \
                self.convertWithBlock(
                    objectId,
                    objectDefinition,
                    objectIdToObjectDefinition
                    )

        else:
            assert False, "haven't gotten to this yet %s" % type(objectDefinition)

    def convertWithBlock(
            self,
            objectId,
            withBlockDescription,
            objectIdToObjectDefinition
            ):
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

    def getFunctionExpressionFromWithBlockDescription(
            self,
            withBlockDescription,
            objectIdToObjectDefinition
            ):
        nativeWithBodyAst, assignedVariables = self._getNativePythonFunctionDefFromWithBlockDescription(
            withBlockDescription,
            objectIdToObjectDefinition
            )

        sourcePath = objectIdToObjectDefinition[withBlockDescription.sourceFileId].path

        foraFunctionExpression = \
            ForaNative.convertPythonAstFunctionDefToForaOrParseErrorWrappingBodyInTryCatch(
                nativeWithBodyAst.asFunctionDef,
                nativeWithBodyAst.extent,
                ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                self.nativeConstantConverter,
                self.nativeListConverter,
                self.nativeTupleConverter,
                self.nativeDictConverter,
                self.pyObjectMixinBaseIVC,
                self.pyObjectGeneratorFactoryIVC,
                list(assignedVariables)
                )

        return foraFunctionExpression

    def _getNativePythonFunctionDefFromWithBlockDescription(
            self,
            withBlockDescription,
            objectIdToObjectDefinition
            ):
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

        assignedVariables = \
            PyAstFreeVariableAnalyses.collectBoundValuesInScope(withBodyAsFunctionAst)

        withBodyAsFunctionAst.body.append(
            self._computeReturnStatementForWithBlockFun(assignedVariables)
            )

        nativeWithBodyAst = PythonAstConverter.convertPythonAstToForaPythonAst(
            withBodyAsFunctionAst,
            sourceLineOffsets
            )

        return nativeWithBodyAst, assignedVariables

    def _computeReturnStatementForWithBlockFun(self, assignedVariables):
        # it would be nice if we could return None here instead of 0 and 0.
        # in this returnTuple, elt 0 is the assigned vars,
        # elt 1 is the traceback (which is not a list so it's handled properly later)
        # and elt 2 is the exception value

        returnTuple = "({" + \
            ",".join(("'%s': %s" % (var, var) for var in assignedVariables)) \
            + "}, 0, 0)"
        return ast.parse("return " + returnTuple).body[0]

    def convertFile(self, objectDefinition):
        return objectDefinition.text

    def _computeRestrictedGraph(self, objectId, dependencyGraph):
        tr = dict()
        dependentIds = dependencyGraph[objectId]

        for dependentId in dependentIds:
            tr[dependentId] = dependencyGraph[dependentId]

        tr[objectId] = dependentIds

        return tr

    def convertClassInstanceDescription(
            self,
            objectId,
            classInstanceDescription
            ):
        classMemberNameToImplVal = {
            classMemberName: self.convertedValues[memberId] for \
            classMemberName, memberId in \
            classInstanceDescription.classMemberNameToClassMemberId.iteritems()
            }
        classImplVal = self.convertedValues[classInstanceDescription.classId]

        #note that we need to strip off the first character of membernames defined in the
        #class implval because the object holds 'x' as '@x' so that it doesn't capture
        #all references to 'x'
        classMembersInForaDeclarationOrder = \
            [str(val)[1:] for val in classImplVal.getDataMembers]

        assert set(classMembersInForaDeclarationOrder) == \
            set(classMemberNameToImplVal.keys()), "%s vs %s" % (
                set(classMembersInForaDeclarationOrder),
                set(classMemberNameToImplVal.keys())
                )

        classMemberImplVals = []
        for classMemberName in classMembersInForaDeclarationOrder:
            ivc = classMemberNameToImplVal[classMemberName]
            classMemberImplVals.append(ivc)

        applyArgs = [classImplVal, createInstanceImplVal] + classMemberImplVals

        self.convertedValues[objectId] = ForaNative.simulateApply(
            ForaNative.ImplValContainer(
                tuple(applyArgs)
                )
            )

    def convertStronglyConnectedComponentWithOneFunctionOrClass(
            self,
            objectId,
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            ):
        foraExpression = \
            self.convertPyClassOrFunctionDefinitionToForaFunctionExpression(
                classOrFunctionDefinition,
                objectIdToObjectDefinition
                )

        renamedVariableMapping = {}

        for freeVariableMemberAccessChain, dependentId in \
            classOrFunctionDefinition.freeVariableMemberAccessChainsToId.iteritems():
            renamedVariableMapping[freeVariableMemberAccessChain] = \
                self.convertedValues[dependentId]

        self.convertedValues[objectId] = \
            self.specializeFreeVariableMemberAccessChainsAndEvaluate(
                foraExpression,
                renamedVariableMapping
                )


    def specializeFreeVariableMemberAccessChainsAndEvaluate(
            self,
            foraExpression,
            renamedVariableMapping
            ):
        foraExpression, renamedVariableMapping = \
            self.specializeFreeVariableMemberAccessChains(
                foraExpression,
                renamedVariableMapping
                )

        allAreIVC = True
        for k, v in renamedVariableMapping.iteritems():
            if not isinstance(v, ForaNative.ImplValContainer):
                allAreIVC = False

        if allAreIVC:
            return ForaNative.evaluateRootLevelCreateObjectExpression(
                foraExpression,
                renamedVariableMapping
                )
        else:
            #function that evaluates the CreateObject. Args are the free variables, in lexical order
            expressionAsIVC = foraExpression.toFunctionImplval(False)

            args = []
            for f in foraExpression.freeVariables:
                args.append(renamedVariableMapping[f])

            res = ComputedValue.ComputedValue(args=(expressionAsIVC, callImplVal) + tuple(args))

            return res

    def specializeFreeVariableMemberAccessChains(
            self, expr, freeVariableMemberAccessChainToImplValMap
            ):
        renamedVariableMapping = {}
        for chain, implval in freeVariableMemberAccessChainToImplValMap.iteritems():
            assert isinstance(chain, str)
            chain = chain.split('.')

            if len(chain) == 1:
                renamedVariableMapping[chain[0]] = implval

            else:
                newName = Expression.freshVarname('_'.join(chain), set(expr.mentionedVariables))
                renamedVariableMapping[newName] = implval
                expr = expr.rebindFreeVariableMemberAccessChain(
                    chain,
                    newName
                    )

        return expr, renamedVariableMapping


    def convertPyClassOrFunctionDefinitionToForaFunctionExpression(
            self,
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            ):
        pyAst = self.convertClassOrFunctionDefinitionToNativePyAst(
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            )

        assert pyAst is not None

        sourcePath = objectIdToObjectDefinition[classOrFunctionDefinition.sourceFileId].path

        tr = None
        if isinstance(classOrFunctionDefinition, TypeDescription.FunctionDefinition):
            if isinstance(pyAst, ForaNative.PythonAstStatement) and pyAst.isFunctionDef():
                tr = ForaNative.convertPythonAstFunctionDefToForaOrParseError(
                    pyAst.asFunctionDef,
                    pyAst.extent,
                    ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                    self.nativeConstantConverter,
                    self.nativeListConverter,
                    self.nativeTupleConverter,
                    self.nativeDictConverter,
                    self.pyObjectMixinBaseIVC,
                    self.pyObjectGeneratorFactoryIVC
                    )
            else:
                assert pyAst.isLambda()
                tr = ForaNative.convertPythonAstLambdaToForaOrParseError(
                    pyAst.asLambda,
                    pyAst.extent,
                    ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                    self.nativeConstantConverter,
                    self.nativeListConverter,
                    self.nativeTupleConverter,
                    self.nativeDictConverter,
                    self.pyObjectMixinBaseIVC,
                    self.pyObjectGeneratorFactoryIVC
                    )

        elif isinstance(classOrFunctionDefinition, TypeDescription.ClassDefinition):
            tr = ForaNative.convertPythonAstClassDefToForaOrParseError(
                pyAst.asClassDef,
                pyAst.extent,
                ForaNative.CodeDefinitionPoint.ExternalFromStringList([sourcePath]),
                self.nativeConstantConverter,
                self.nativeListConverter,
                self.nativeTupleConverter,
                self.nativeDictConverter,
                self.pyObjectMixinBaseIVC,
                self.pyObjectGeneratorFactoryIVC
                )

        else:
            assert False

        if isinstance(tr, ForaNative.PythonToForaConversionError):
            raise pyfora.PythonToForaConversionError(tr)

        return tr

    def convertClassOrFunctionDefinitionToNativePyAst(
            self,
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            ):
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
            if pyforaValue != Symbol_uninitialized:
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
                assert value.isVectorOfChar()

                contents = vectorContentsExtractor(value)
                if contents is None:
                    return transformer.transformStringThatNeedsLoading(len(value))
                else:
                    return transformer.transformPrimitive(contents)

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

            value = self.singletonAndExceptionConverter.convertInvalidPyforaOperationInstance(implval)
            if value is not None:
                return transformer.transformInvalidPythonOperationException(value)

        value = self.nativeTupleConverter.invertTuple(implval)
        if value is not None:
            return transformer.transformTuple(
                [self.transformPyforaImplval(x, transformer, vectorContentsExtractor) for x in value]
                )

        value = self.nativeDictConverter.invertDict(implval)
        if value is not None:
            return transformer.transformDict(
                keys=[self.transformPyforaImplval(k, transformer, vectorContentsExtractor) for k in value.keys()],
                values=[self.transformPyforaImplval(v, transformer, vectorContentsExtractor) for v in value.values()]
                )

        listItemsAsVector = self.nativeListConverter.invertList(implval)
        if listItemsAsVector is not None:
            contents = vectorContentsExtractor(listItemsAsVector)
            if contents is None:
                return transformer.transformListThatNeedsLoading(len(listItemsAsVector))
            else:
                return transformer.transformList(
                    [self.transformPyforaImplval(x,transformer, vectorContentsExtractor) for x in contents]
                    )

        if implval.isTuple():
            stackTraceAsJsonOrNone = self.getStackTraceAsJsonOrNone(implval)
            if stackTraceAsJsonOrNone is not None:
                return stackTraceAsJsonOrNone

        if implval.isObject():
            defPoint = implval.getObjectDefinitionPoint()
            if defPoint is not None:
                objectClass = implval.getObjectClass()
                if objectClass is not None:
                    classObject = self.transformPyforaImplval(objectClass, transformer, vectorContentsExtractor)
                    members = {}

                    for memberName in objectClass.objectMembers:
                        if memberName is not None:
                            member = implval.getObjectLexicalMember(memberName)
                            if member is not None and member[1] is None:
                                members[str(memberName)[1:]] = self.transformPyforaImplval(member[0], transformer, vectorContentsExtractor)

                    return transformer.transformClassInstance(classObject, members)
                else:
                    members = {}
                    lexicalMembers = implval.objectLexicalMembers
                    for memberAndBindingSequence in lexicalMembers.iteritems():
                        #if the binding sequence is empty, then this binding refers to 'self'
                        if memberAndBindingSequence[1][0]:
                            memberName = memberAndBindingSequence[0]
                            member = implval.getObjectLexicalMember(memberName)
                            if member is not None and member[1] is None:
                                members[str(memberName)] = self.transformPyforaImplval(member[0], transformer, vectorContentsExtractor)

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
                if memberAndBindingSequence[1][0]:
                    memberName = memberAndBindingSequence[0]
                    member = implval.getObjectLexicalMember(memberName)
                    if member is not None and member[1] is None:
                        members[str(memberName)] = self.transformPyforaImplval(member[0], transformer, vectorContentsExtractor)

            return transformer.transformClassObject(
                    defPoint.defPoint.asExternal.paths[0],
                    defPoint.range.start.line,
                    members
                    )

        raise pyfora.ForaToPythonConversionError(
            "Computation references a value of type %s that cannot be translated back to python."
                % (str(implval.type))
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
            'stacktrace': [x for x in [formatCodeLocation(c) for c in codeLocations] if x is not None]
            }

