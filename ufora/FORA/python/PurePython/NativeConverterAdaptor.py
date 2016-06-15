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


import ufora.FORA.python.Expression as Expression
import ufora.FORA.python.PurePython.PythonAstConverter as PythonAstConverter
import ufora.FORA.python.PurePython.ConstantConverter as ConstantConverter
import ufora.BackendGateway.ComputedValue.ComputedValue as ComputedValue

import ast
import pyfora
import pyfora.pyAst.PyAstUtil as PyAstUtil
import pyfora.TypeDescription as TypeDescription

import ufora.native.FORA as ForaNative

from collections import namedtuple


ImplValObjectAndMemberToObjectIdMap = namedtuple('ImplValObjectAndMemberToObjectIdMap',
                                                 ['implVal', 'memberToObjectIdMap'])
emptyCodeDefinitionPoint = ForaNative.CodeDefinitionPoint.ExternalFromStringList([])
empytObjectExpression = ForaNative.parseStringToExpression(
    "object {}",
    emptyCodeDefinitionPoint,
    ""
    )
Symbol_Call = ForaNative.makeSymbol("Call")
Symbol_CreateInstance = ForaNative.makeSymbol("CreateInstance")
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


class NativeConverterAdaptor(object):
    def __init__(self,
                 nativeConstantConverter,
                 nativeDictConverter,
                 nativeTupleConverter,
                 nativeListConverter,
                 vdmOverride,
                 builtinMemberMapping,
                 purePythonModuleImplVal):
        self.boundExpressions = {}

        self.constantConverter = ConstantConverter.ConstantConverter(
            nativeConstantConverter=nativeConstantConverter
            )
        self.nativeDictConverter = nativeDictConverter
        self.nativeTupleConverter = nativeTupleConverter
        self.nativeListConverter = nativeListConverter
        self.vdm_ = vdmOverride

        self.nativeConverter = ForaNative.makePythonAstConverter(
            nativeConstantConverter,
            nativeListConverter,
            nativeTupleConverter,
            nativeDictConverter,
            purePythonModuleImplVal,
            builtinMemberMapping
            )

    def createList(self, listOfConvertedValues):
        return self.nativeListConverter.createList(
            listOfConvertedValues,
            self.vdm_
            )

    def invertList(self, implval):
        return self.nativeListConverter.invertList(implval)

    def createListOfPrimitives(self, value):
        return self.nativeListConverter.createListOfPrimitives(
            value,
            self.constantConverter.nativeConstantConverter,
            self.vdm_
            )

    def convertConstant(self, value):
        return self.constantConverter.convert(value)

    def invertForaConstant(self, foraConstant):
        return self.constantConverter.invertForaConstant(foraConstant)

    def createTuple(self, listOfConvertedValues):
        return self.nativeTupleConverter.createTuple(listOfConvertedValues)

    def invertTuple(self, tupleIVC):
        return self.nativeTupleConverter.invertTuple(tupleIVC)

    def createDict(self, convertedKeysAndVals):
        return self.nativeDictConverter.createDict(convertedKeysAndVals)

    def invertDict(self, dictIVC):
        return self.nativeDictConverter.invertDict(dictIVC)

    def convertClassInstanceDescription(self, objectId, classInstanceDescription, convertedValues):
        classMemberNameToImplVal = {
            classMemberName: convertedValues[memberId]
            for classMemberName, memberId in
            classInstanceDescription.classMemberNameToClassMemberId.iteritems()
            }
        classImplVal = convertedValues[classInstanceDescription.classId]

        if classImplVal.isSymbol():
            convertedValues[objectId] = classImplVal
            return

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

        convertedValues[objectId] = convertedValueOrNone

    def convertMutuallyRecursiveObjects(self,
                                        objectIdToObjectDefinition,
                                        stronglyConnectedComponent,
                                        convertedValues):
        (createObjectExpression, memberToObjectIdMap) = \
            self._getCreateObjectExpressionAndMemberToObjectIdMap(
                objectIdToObjectDefinition,
                stronglyConnectedComponent
                )

        return ImplValObjectAndMemberToObjectIdMap(
            implVal=self._bindDependentValuesToCreateObjectExpression(
                createObjectExpression,
                memberToObjectIdMap,
                objectIdToObjectDefinition,
                convertedValues
                ),
            memberToObjectIdMap=memberToObjectIdMap)

    def convertClassOrFunctionDefinitionWithNoDependencies(
            self,
            classOrFunctionDefinition,
            objectIdToObjectDefinition,
            convertedValues):
                

        foraExpression = self._convertPyClassOrFunctionDefinitionToForaFunctionExpression(
            classOrFunctionDefinition,
            objectIdToObjectDefinition
            )

        renamedVariableMapping = {}

        for freeVariableMemberAccessChain, dependentId in \
            classOrFunctionDefinition.freeVariableMemberAccessChainsToId.iteritems():
            renamedVariableMapping[freeVariableMemberAccessChain] = \
                convertedValues[dependentId]

        if isinstance(classOrFunctionDefinition, TypeDescription.ClassDefinition):
            for i, baseId in enumerate(classOrFunctionDefinition.baseClassIds):
                renamedVariableMapping["baseClass%d" % i] = convertedValues[baseId]

        return self._specializeFreeVariableMemberAccessChainsAndEvaluate(
                foraExpression,
                renamedVariableMapping
                )

    def _getCreateObjectExpressionAndMemberToObjectIdMap(self,
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
                self._convertPyClassOrFunctionDefinitionToForaFunctionExpression(
                    objectDefinition,
                    objectIdToObjectDefinition
                    )
        # at this point, naiveConvertedFunctions is a map: objectId -> functionExpr

        # renamedObjectMapping is a map: objectId -> varname,
        # where varname is (essentially) just the hash of the corresponding functionExpr
        renamedObjectMapping = self._computeRenamedObjectMapping(
            naiveConvertedFunctions
            )

        # replace the known free var chains in the strongly connected component
        # with the varnames coming from the renamedObjectMapping
        convertedFunctions = self._replaceKnownMemberChainsWithRenamedVariables(
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

    def _computeRenamedObjectMapping(self, objectIdToForaFunctionExpression):
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

    def _replaceKnownMemberChainsWithRenamedVariables(self,
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

    @staticmethod
    def _convertClassOrFunctionDefinitionToNativePyAst(classOrFunctionDefinition,
                                                      objectIdToObjectDefinition):
        sourceText = objectIdToObjectDefinition[classOrFunctionDefinition.sourceFileId].text

        pyAst = PythonAstConverter.parseStringToPythonAst(sourceText)

        assert pyAst is not None

        pyAst = pyAst.functionClassOrLambdaDefAtLine(classOrFunctionDefinition.lineNumber)

        assert pyAst is not None, (sourceText, classOrFunctionDefinition.lineNumber)

        return pyAst

    def _convertPyClassOrFunctionDefinitionToForaFunctionExpression(self,
                                                                   classOrFunctionDefinition,
                                                                   objectIdToObjectDefinition):
        pyAst = self._convertClassOrFunctionDefinitionToNativePyAst(
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

    def _bindDependentValuesToCreateObjectExpression(self,
                                                    createObjectExpression,
                                                    renamedObjectMapping,
                                                    objectIdToObjectDefinition,
                                                    convertedValues):
        stronglyConnectedComponent = renamedObjectMapping.keys()

        renamedVariableMapping = dict()

        for objectId in stronglyConnectedComponent:
            for freeVariableMemberAccessChain, dependentId in \
                objectIdToObjectDefinition[objectId].freeVariableMemberAccessChainsToId.iteritems():
                if dependentId not in stronglyConnectedComponent:
                    renamedVariableMapping[freeVariableMemberAccessChain] = \
                        convertedValues[dependentId]

        return self._specializeFreeVariableMemberAccessChainsAndEvaluate(
            createObjectExpression,
            renamedVariableMapping
            )

    def convertWithBlock(self,
                         withBlockDescription,
                         objectIdToObjectDefinition,
                         convertedValues):
        foraFunctionExpression = self._getFunctionExpressionFromWithBlockDescription(
            withBlockDescription,
            objectIdToObjectDefinition
            )

        renamedVariableMapping = {}

        for freeVariableMemberAccessChain, dependentId in \
            withBlockDescription.freeVariableMemberAccessChainsToId.iteritems():
            renamedVariableMapping[freeVariableMemberAccessChain] = \
                convertedValues[dependentId]

        return self._specializeFreeVariableMemberAccessChainsAndEvaluate(
            foraFunctionExpression,
            renamedVariableMapping
            )

    def _reduceFreeVariableMemberAccessChains(self,
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

    def _specializeFreeVariableMemberAccessChainsAndEvaluate(self,
                                                            foraExpression,
                                                            renamedVariableMapping):
        foraExpression, renamedVariableMapping = \
            self._reduceFreeVariableMemberAccessChains(
                foraExpression,
                renamedVariableMapping
                )

        foraExpression = self._handleUnconvertibleValuesInExpression(
            foraExpression,
            renamedVariableMapping
            )

        return self._specializeFreeVariablesAndEvaluate(
            foraExpression,
            renamedVariableMapping
            )

    def _handleUnconvertibleValuesInExpression(
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

    def _specializeFreeVariablesAndEvaluate(
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

    def _getFunctionExpressionFromWithBlockDescription(self,
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

