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
import pyfora
import pyfora.Exceptions as Exceptions
import pyfora.pyAst.PyAstFreeVariableAnalyses as PyAstFreeVariableAnalyses
import pyfora.RemotePythonObject as RemotePythonObject
import pyfora.Future as Future
import pyfora.NamedSingletons as NamedSingletons
import pyfora.PyforaWithBlock as PyforaWithBlock
import pyfora.PyforaInspect as PyforaInspect
import pyfora.pyAst.PyAstUtil as PyAstUtil
from pyfora.TypeDescription import isPrimitive
from pyfora.PyforaInspect import PyforaInspectError

import logging
import traceback
import __builtin__
import ast


class UnresolvedFreeVariableException(Exception):
    def __init__(self, freeVariable, contextName):
        super(UnresolvedFreeVariableException, self).__init__()
        self.freeVarChainWithPos = freeVariable
        self.contextNameOrNone = contextName


class UnresolvedFreeVariableExceptionWithTrace(Exception):
    def __init__(self, message, trace=None):
        super(UnresolvedFreeVariableExceptionWithTrace, self).__init__()
        self.message = message
        if trace is None:
            self.trace = []
        else:
            self.trace = trace
    def addToTrace(self, elmt):
        Exceptions.checkTraceElement(elmt)
        self.trace.insert(0, elmt)


def _convertUnresolvedFreeVariableExceptionAndRaise(e, sourceFileName):
    logging.error(
        "Converter raised an UnresolvedFreeVariableException exception: %s",
        traceback.format_exc())
    chainWithPos = e.freeVarChainWithPos
    varLine = chainWithPos.pos.lineno
    varName = chainWithPos.var[0]
    raise UnresolvedFreeVariableExceptionWithTrace(
        '''unable to resolve free variable '%s' for pyfora conversion''' % varName,
        [Exceptions.makeTraceElement(sourceFileName, varLine)]
        )


def isClassInstance(pyObject):
    return hasattr(pyObject, "__class__")


class _AClassWithAMethod:
    def f(self):
        pass


instancemethod = type(_AClassWithAMethod().f)


class _Unconvertible(object):
    pass


class _FunctionDefinition(object):
    def __init__(self, sourceFileId, lineNumber, freeVariableMemberAccessChainsToId):
        self.sourceFileId = sourceFileId
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainsToId = \
            freeVariableMemberAccessChainsToId


class _ClassDefinition(object):
    def __init__(self, sourceFileId, lineNumber, freeVariableMemberAccessChainsToId):
        self.sourceFileId = sourceFileId
        self.lineNumber = lineNumber
        self.freeVariableMemberAccessChainsToId = \
            freeVariableMemberAccessChainsToId


class _FileDescription(object):
    _fileTextCache = {}

    def __init__(self, fileName, fileText):
        self.fileName = fileName
        self.fileText = fileText

    @classmethod
    def cachedFromArgs(cls, fileName, fileText=None):
        if fileName in cls._fileTextCache:
            return cls._fileTextCache[fileName]

        if fileText is None:
            fileText = "".join(PyforaInspect.getlines(fileName))

        tr = cls(fileName, fileText)
        cls._fileTextCache[fileName] = tr
        return tr


class PyObjectWalker(object):
    """
    `PyObjectWalker`: walk a live python object, registering its pieces with an
    `ObjectRegistry`

    The main, and only publicly viewable function on this class is `walkPyObject`

    Attributes:
        _`purePythonClassMapping`: a `PureImplementationMapping` -- used to
            "replace" python objects in an python object graph by a "Pure"
            python class. For example, treat this `np.array` as a
        `PurePython.SomePureImplementationOfNumpyArray`.
        `_convertedObjectCache`: a mapping from python id -> pure instance
        `_pyObjectIdToObjectId`: mapping from python id -> id registered in
            `self.objectRegistry`
        `_objectRegistry`: an `ObjectRegistry` which holds an image of the
            objects we visit.

    """
    def __init__(self, purePythonClassMapping, objectRegistry):
        assert purePythonClassMapping is not None

        for singleton in NamedSingletons.pythonSingletonToName:
            if purePythonClassMapping.canMap(singleton):
                raise UserWarning(
                    "You provided a mapping that applies to %s, "
                    "which already has a direct mapping" % singleton
                    )

        self._purePythonClassMapping = purePythonClassMapping
        self._convertedObjectCache = {}
        self._pyObjectIdToObjectId = {}
        self._objectRegistry = objectRegistry

    def _allocateId(self, pyObject):
        objectId = self._objectRegistry.allocateObject()
        self._pyObjectIdToObjectId[id(pyObject)] = objectId

        return objectId

    def walkPyObject(self, pyObject):
        """
        `walkPyObject`: recursively traverse a live python object,
        registering its "pieces" with an `ObjectRegistry`
        (`self.objectRegistry`).

        Note that we use python `id`s for caching in this class,
        which means it cannot be used in cases where `id`s might get
        reused (recall they are just memory addresses).

        `objectId`s are assigned to all pieces of the python object.

        Returns:
            An `int`, the `objectId` of the root python object.
        """
        if id(pyObject) in self._pyObjectIdToObjectId:
            return self._pyObjectIdToObjectId[id(pyObject)]

        if id(pyObject) in self._convertedObjectCache:
            pyObject = self._convertedObjectCache[id(pyObject)]
        elif self._purePythonClassMapping.canMap(pyObject):
            pureInstance = self._purePythonClassMapping.mappableInstanceToPure(
                pyObject
                )
            self._convertedObjectCache[id(pyObject)] = pureInstance
            pyObject = pureInstance

        objectId = self._allocateId(pyObject)

        if pyObject is pyfora.connect:
            self._registerUnconvertible(objectId)
            return objectId

        try:
            self._walkPyObject(pyObject, objectId)
        except Exceptions.CantGetSourceTextError:
            self._registerUnconvertible(objectId)
        except PyforaInspectError:
            self._registerUnconvertible(objectId)

        return objectId

    def _walkPyObject(self, pyObject, objectId):
        if isinstance(pyObject, RemotePythonObject.RemotePythonObject):
            self._registerRemotePythonObject(objectId, pyObject)
        elif isinstance(pyObject, Future.Future):
            #it would be better to register the future and do a second pass of walking
            self._walkPyObject(pyObject.result(), objectId)
        elif isinstance(pyObject, _FileDescription):
            self._registerFileDescription(objectId, pyObject)
        elif isinstance(pyObject, Exception) and pyObject.__class__ in \
           NamedSingletons.pythonSingletonToName:
            self._registerBuiltinExceptionInstance(objectId, pyObject)
        elif isinstance(pyObject, (type, type(isinstance))) and \
           pyObject in NamedSingletons.pythonSingletonToName:
            self._registerNamedSingleton(
                objectId,
                NamedSingletons.pythonSingletonToName[pyObject]
                )
        elif isinstance(pyObject, PyforaWithBlock.PyforaWithBlock):
            self._registerWithBlock(objectId, pyObject)
        elif isinstance(pyObject, _Unconvertible):
            self._registerUnconvertible(objectId)
        elif isinstance(pyObject, tuple):
            self._registerTuple(objectId, pyObject)
        elif isinstance(pyObject, list):
            self._registerList(objectId, pyObject)
        elif isinstance(pyObject, dict):
            self._registerDict(objectId, pyObject)
        elif isPrimitive(pyObject):
            self._registerPrimitive(objectId, pyObject)
        elif PyforaInspect.isfunction(pyObject):
            self._registerFunction(objectId, pyObject)
        elif PyforaInspect.isclass(pyObject):
            self._registerClass(objectId, pyObject)
        elif isinstance(pyObject, instancemethod):
            self._registerInstanceMethod(objectId, pyObject)
        elif isClassInstance(pyObject):
            self._registerClassInstance(objectId, pyObject)
        else:
            assert False, "don't know what to do with %s" % pyObject

    def _registerRemotePythonObject(self, objectId, remotePythonObject):
        """
        `_registerRemotePythonObject`: register a remotePythonObject
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineRemotePythonObject(
            objectId,
            remotePythonObject._pyforaComputedValueArg()
            )

    def _registerFileDescription(self, objectId, fileDescription):
        """
        `_registerFileDescription`: register a `_FileDescription`
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineFile(
            objectId=objectId,
            path=fileDescription.fileName,
            text=fileDescription.fileText
            )

    def _registerBuiltinExceptionInstance(self, objectId, builtinExceptionInstance):
        """
        `_registerBuiltinExceptionInstance`: register a `builtinExceptionInstance`
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the args of the instance.
        """
        argsId = self.walkPyObject(builtinExceptionInstance.args)

        self._objectRegistry.defineBuiltinExceptionInstance(
            objectId,
            NamedSingletons.pythonSingletonToName[
                builtinExceptionInstance.__class__
                ],
            argsId
            )

    def _registerNamedSingleton(self, objectId, singletonName):
        """
        `_registerNamedSingleton`: register a `NamedSingleton`
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.defineNamedSingleton(objectId, singletonName)

    def _registerTuple(self, objectId, tuple_):
        """
        `_registerTuple`: register a `tuple` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the values in the tuple.
        """
        memberIds = [self.walkPyObject(val) for val in tuple_]

        self._objectRegistry.defineTuple(
            objectId=objectId,
            memberIds=memberIds
            )

    def _registerList(self, objectId, list_):
        """
        `_registerList`: register a `list` instance with `self.objectRegistry`.
        Recursively call `walkPyObject` on the values in the list.
        """
        if all(isPrimitive(val) for val in list_):
            self._registerPrimitive(objectId, list_)
        else:
            memberIds = [self.walkPyObject(val) for val in list_]

            self._objectRegistry.defineList(
                objectId=objectId,
                memberIds=memberIds
                )

    def _registerPrimitive(self, objectId, primitive):
        """
        `_registerPrimitive`: register a primitive (defined by `isPrimitive`)
        (a terminal node in a python object graph) with `self.objectRegistry`
        """
        self._objectRegistry.definePrimitive(
            objectId,
            primitive
            )

    def _registerDict(self, objectId, dict_):
        """
        `_registerDict`: register a `dict` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the keys and values in the dict
        """
        keyIds, valueIds = [], []
        for k, v in dict_.iteritems():
            keyIds.append(self.walkPyObject(k))
            valueIds.append(self.walkPyObject(v))

        self._objectRegistry.defineDict(
            objectId=objectId,
            keyIds=keyIds,
            valueIds=valueIds
            )

    def _registerInstanceMethod(self, objectId, pyObject):
        """
        `_registerInstanceMethod`: register an `instancemethod` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the object to which the instance is
        bound, and encode alongside the name of the method.
        """
        instance = pyObject.__self__
        methodName = pyObject.__name__

        instanceId = self.walkPyObject(instance)

        self._objectRegistry.defineInstanceMethod(
            objectId=objectId,
            instanceId=instanceId,
            methodName=methodName
            )


    def _registerClassInstance(self, objectId, classInstance):
        """
        `_registerClassInstance`: register a `class` instance
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the class of the `classInstance`
        and on the data members of the instance.
        """
        classObject = classInstance.__class__
        classId = self.walkPyObject(classObject)

        dataMemberNames = classInstance.__dict__.keys() if hasattr(classInstance, '__dict__') \
            else PyAstUtil.collectDataMembersSetInInit(classObject)
        classMemberNameToClassMemberId = {}
        for dataMemberName in dataMemberNames:
            memberId = self.walkPyObject(getattr(classInstance, dataMemberName))
            classMemberNameToClassMemberId[dataMemberName] = memberId

        self._objectRegistry.defineClassInstance(
            objectId=objectId,
            classId=classId,
            classMemberNameToClassMemberId=classMemberNameToClassMemberId
            )

    def _registerWithBlock(self, objectId, pyObject):
        """
        `_registerWithBlock`: register a `PyforaWithBlock.PyforaWithBlock`
        with `self.objectRegistry`.

        Recursively call `walkPyObject` on the resolvable free variable
        member access chains in the block and on the file object.
        """
        lineNumber = pyObject.lineNumber
        sourceTree = PyAstUtil.pyAstFromText(pyObject.sourceText)
        withBlockAst = PyAstUtil.withBlockAtLineNumber(sourceTree, lineNumber)

        withBlockFun = ast.FunctionDef(
            name="",
            args=ast.arguments(args=[], defaults=[], kwarg=None, vararg=None),
            body=withBlockAst.body,
            decorator_list=[],
            lineno=lineNumber,
            col_offset=0
            )

        if PyAstUtil.hasReturnInOuterScope(withBlockFun):
            raise Exceptions.BadWithBlockError(
                "return statement not supported in pyfora with-block (line %s)" %
                PyAstUtil.getReturnLocationsInOuterScope(withBlockFun)[0])

        if PyAstUtil.hasYieldInOuterScope(withBlockFun):
            raise Exceptions.BadWithBlockError(
                "yield expression not supported in pyfora with-block (line %s)" %
                PyAstUtil.getYieldLocationsInOuterScope(withBlockFun)[0])

        freeVariableMemberAccessChainsWithPositions = \
            self._freeMemberAccessChainsWithPositions(withBlockFun)

        boundValuesInScopeWithPositions = \
            PyAstFreeVariableAnalyses.collectBoundValuesInScope(
                withBlockFun, getPositions=True)

        for boundValueWithPosition in boundValuesInScopeWithPositions:
            val, pos = boundValueWithPosition
            if val not in pyObject.unboundLocals and val in pyObject.boundVariables:
                freeVariableMemberAccessChainsWithPositions.add(
                    PyAstFreeVariableAnalyses.VarWithPosition(var=(val,), pos=pos)
                    )

        try:
            freeVariableMemberAccessChainResolutions = \
                self._resolveFreeVariableMemberAccessChains(
                    freeVariableMemberAccessChainsWithPositions, pyObject.boundVariables
                    )
        except UnresolvedFreeVariableException as e:
            _convertUnresolvedFreeVariableExceptionAndRaise(e, pyObject.sourceFileName)

        try:
            processedFreeVariableMemberAccessChainResolutions = {}
            for chain, (resolution, position) in \
                freeVariableMemberAccessChainResolutions.iteritems():
                processedFreeVariableMemberAccessChainResolutions['.'.join(chain)] = \
                    self.walkPyObject(resolution)
        except UnresolvedFreeVariableExceptionWithTrace as e:
            e.addToTrace(
                Exceptions.makeTraceElement(
                    path=pyObject.sourceFileName,
                    lineNumber=position.lineno
                    )
                )
            raise

        sourceFileId = self.walkPyObject(
            _FileDescription.cachedFromArgs(
                fileName=pyObject.sourceFileName
                )
            )

        self._objectRegistry.defineWithBlock(
            objectId=objectId,
            freeVariableMemberAccessChainsToId=\
                processedFreeVariableMemberAccessChainResolutions,
            sourceFileId=sourceFileId,
            lineNumber=lineNumber
            )

    def _registerFunction(self, objectId, function):
        """
        `_registerFunction`: register a python function with `self.objectRegistry.

        Recursively call `walkPyObject` on the resolvable free variable member
        access chains in the function, as well as on the source file object.
        """
        functionDescription = self._classOrFunctionDefinition(
            function,
            classOrFunction=_FunctionDefinition
            )

        self._objectRegistry.defineFunction(
            objectId=objectId,
            sourceFileId=functionDescription.sourceFileId,
            lineNumber=functionDescription.lineNumber,
            scopeIds=functionDescription.freeVariableMemberAccessChainsToId
            )

    def _registerClass(self, objectId, pyObject):
        """
        `_registerClass`: register a python class with `self.objectRegistry.

        Recursively call `walkPyObject` on the resolvable free variable member
        access chains in the class, as well as on the source file object.
        """
        classDescription = self._classOrFunctionDefinition(
            pyObject,
            classOrFunction=_ClassDefinition
            )
        assert all(id(base) in self._pyObjectIdToObjectId for base in pyObject.__bases__)

        self._objectRegistry.defineClass(
            objectId=objectId,
            sourceFileId=classDescription.sourceFileId,
            lineNumber=classDescription.lineNumber,
            scopeIds=classDescription.freeVariableMemberAccessChainsToId,
            baseClassIds=[self._pyObjectIdToObjectId[id(base)] for base in pyObject.__bases__]
            )

    def _registerUnconvertible(self, objectId):
        self._objectRegistry.defineUnconvertible(objectId)

    def _classOrFunctionDefinition(self, pyObject, classOrFunction):
        """
        `_classOrFunctionDefinition: create a `_FunctionDefinition` or
        `_ClassDefinition` out of a python class or function, recursively visiting
        the resolvable free variable member access chains in `pyObject` as well
        as the source file object.

        Args:
            `pyObject`: a python class or function.
            `classOrFunction`: should either be `_FunctionDefinition` or
                `_ClassDefinition`.

        Returns:
            a `_FunctionDefinition` or `_ClassDefinition`.

        """
        if pyObject.__name__ == '__inline_fora':
            raise Exceptions.PythonToForaConversionError(
                "in pyfora, '__inline_fora' is a reserved word"
                )

        sourceFileText, sourceFileName = PyAstUtil.getSourceFilenameAndText(pyObject)

        _, sourceLine = PyAstUtil.getSourceLines(pyObject)

        sourceAst = PyAstUtil.pyAstFromText(sourceFileText)

        if classOrFunction is _FunctionDefinition:
            pyAst = PyAstUtil.functionDefOrLambdaAtLineNumber(sourceAst, sourceLine)
        else:
            assert classOrFunction is _ClassDefinition
            pyAst = PyAstUtil.classDefAtLineNumber(sourceAst, sourceLine)

        assert sourceLine == pyAst.lineno

        try:
            freeVariableMemberAccessChainResolutions = \
                self._computeAndResolveFreeVariableMemberAccessChainsInAst(
                    pyObject, pyAst
                    )
        except UnresolvedFreeVariableException as e:
            _convertUnresolvedFreeVariableExceptionAndRaise(e, sourceFileName)

        try:
            processedFreeVariableMemberAccessChainResolutions = {}
            for chain, (resolution, location) in \
                freeVariableMemberAccessChainResolutions.iteritems():
                processedFreeVariableMemberAccessChainResolutions['.'.join(chain)] = \
                    self.walkPyObject(resolution)
        except UnresolvedFreeVariableExceptionWithTrace as e:
            e.addToTrace(
                Exceptions.makeTraceElement(
                    path=sourceFileName,
                    lineNumber=location[0]
                    )
                )
            raise

        sourceFileId = self.walkPyObject(
            _FileDescription.cachedFromArgs(
                fileName=sourceFileName,
                fileText=sourceFileText
                )
            )

        return classOrFunction(
            sourceFileId=sourceFileId,
            lineNumber=sourceLine,
            freeVariableMemberAccessChainsToId=\
                processedFreeVariableMemberAccessChainResolutions
            )

    @staticmethod
    def _freeMemberAccessChainsWithPositions(pyAst):
        # ATz: just added 'False' as a 2nd argument, but we may need to check
        # that whenever pyAst is a FunctionDef node, its context is not a class
        # (i.e., it is not an instance method). In that case, we need to pass
        # 'True' as the 2nd argument.

        def is_pureMapping_call(node):
            return isinstance(node, ast.Call) and \
                isinstance(node.func, ast.Name) and \
                node.func.id == 'pureMapping'

        freeVariableMemberAccessChains = \
            PyAstFreeVariableAnalyses.getFreeVariableMemberAccessChains(
                pyAst,
                isClassContext=False,
                getPositions=True,
                exclude_predicate=is_pureMapping_call
                )

        return freeVariableMemberAccessChains

    def _resolveChainByDict(self, chainWithPosition, boundVariables):
        """
        `_resolveChainByDict`: look up a free variable member access chain, `chain`,
        in a dictionary of resolutions, `boundVariables`, or in `__builtin__` and
        return a tuple (subchain, resolution, location).
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in boundVariables:
            rootValue = boundVariables[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            raise UnresolvedFreeVariableException(chainWithPosition, None)

        return self._computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)


    def _resolveChainInPyObject(self, chainWithPosition, pyObject, pyAst):
        """
        This name could be improved.

        Returns a `subchain, terminalPyValue, location` tuple: this represents
        the deepest value we can get to in the member chain `chain` on `pyObject`
        taking members only along modules (or "empty" modules)

        """
        subchainAndResolutionOrNone = self._subchainAndResolutionOrNone(pyObject,
                                                                        pyAst,
                                                                        chainWithPosition)
        if subchainAndResolutionOrNone is None:
            raise Exceptions.PythonToForaConversionError(
                "don't know how to resolve %s in %s (line:%s)"
                % (chainWithPosition.var, pyObject, chainWithPosition.pos.lineno)
                )

        subchain, terminalValue, location = subchainAndResolutionOrNone

        if id(terminalValue) in self._convertedObjectCache:
            terminalValue = self._convertedObjectCache[id(terminalValue)]

        return subchain, terminalValue, location

    def _subchainAndResolutionOrNone(self, pyObject, pyAst, chainWithPosition):
        if PyforaInspect.isfunction(pyObject):
            return self._lookupChainInFunction(pyObject, chainWithPosition)

        if PyforaInspect.isclass(pyObject):
            return self._lookupChainInClass(pyObject, pyAst, chainWithPosition)

        return None

    @staticmethod
    def _classMemberFunctions(pyObject):
        return PyforaInspect.getmembers(
            pyObject,
            lambda elt: PyforaInspect.ismethod(elt) or PyforaInspect.isfunction(elt)
            )

    def _lookupChainInClass(self, pyClass, pyAst, chainWithPosition):
        """
        return a pair `(subchain, subchainResolution)`
        where subchain resolves to subchainResolution in pyClass
        """
        memberFunctions = self._classMemberFunctions(pyClass)

        for _, func in memberFunctions:
            # lookup should be indpendent of which function we
            # actually choose. However, the unbound chain may not
            # appear in every member function
            try:
                return self._lookupChainInFunction(func, chainWithPosition)
            except UnresolvedFreeVariableException:
                pass

        baseClassResolutionOrNone = self._resolveChainByBaseClasses(
            pyClass, pyAst, chainWithPosition
            )
        if baseClassResolutionOrNone is not None:
            return baseClassResolutionOrNone

        raise UnresolvedFreeVariableException(chainWithPosition, None)

    def _resolveChainByBaseClasses(self, pyClass, pyAst, chainWithPosition):
        chain = chainWithPosition.var
        position = chainWithPosition.pos

        baseClassChains = [self._getBaseClassChain(base) for base in pyAst.bases]

        if chain in baseClassChains:
            resolution = pyClass.__bases__[baseClassChains.index(chain)]
            return chain, resolution, position

        # note: we could do better here. we could search the class
        # variables of the base class as well
        return None

    def _getBaseClassChain(self, baseAst):
        if isinstance(baseAst, ast.Name):
            return (baseAst.id,)
        if isinstance(baseAst, ast.Attribute):
            return self._getBaseClassChain(baseAst.value) + (baseAst.attr,)

    def _lookupChainInFunction(self, pyFunction, chainWithPosition):
        """
        return a tuple `(subchain, subchainResolution, location)`
        where subchain resolves to subchainResolution in pyFunction
        """
        freeVariable = chainWithPosition.var[0]

        if freeVariable in pyFunction.func_code.co_freevars:
            index = pyFunction.func_code.co_freevars.index(freeVariable)
            try:
                rootValue = pyFunction.__closure__[index].cell_contents
            except Exception as e:
                logging.error("Encountered Exception: %s: %s", type(e).__name__, e)
                logging.error(
                    "Failed to get value for free variable %s\n%s",
                    freeVariable, traceback.format_exc())
                raise UnresolvedFreeVariableException(
                    chainWithPosition, pyFunction.func_name)

        elif freeVariable in pyFunction.func_globals:
            rootValue = pyFunction.func_globals[freeVariable]

        elif hasattr(__builtin__, freeVariable):
            rootValue = getattr(__builtin__, freeVariable)

        else:
            raise UnresolvedFreeVariableException(
                chainWithPosition, pyFunction.func_name)

        return self._computeSubchainAndTerminalValueAlongModules(
            rootValue, chainWithPosition)

    @staticmethod
    def _computeSubchainAndTerminalValueAlongModules(rootValue, chainWithPosition):
        ix = 1
        chain = chainWithPosition.var
        position = chainWithPosition.pos

        subchain, terminalValue = chain[:ix], rootValue

        while PyforaInspect.ismodule(terminalValue):
            if ix >= len(chain):
                #we're terminating at a module
                terminalValue = _Unconvertible()
                break

            if not hasattr(terminalValue, chain[ix]):
                raise Exceptions.PythonToForaConversionError(
                    "Module %s has no member %s" % (str(terminalValue), chain[ix])
                    )

            terminalValue = getattr(terminalValue, chain[ix])
            ix += 1
            subchain = chain[:ix]

        return subchain, terminalValue, position

    def _resolveFreeVariableMemberAccessChains(self,
                                               freeVariableMemberAccessChainsWithPositions,
                                               boundVariables):
        """ Return a dictionary mapping subchains to resolved ids."""
        resolutions = dict()

        for chainWithPosition in freeVariableMemberAccessChainsWithPositions:
            subchain, resolution, position = self._resolveChainByDict(
                chainWithPosition, boundVariables)

            if id(resolution) in self._convertedObjectCache:
                resolution = self._convertedObjectCache[id(resolution)][1]

            resolutions[subchain] = (resolution, position)

        return resolutions

    def _computeAndResolveFreeVariableMemberAccessChainsInAst(self, pyObject, pyAst):
        resolutions = {}

        for chainWithPosition in self._freeMemberAccessChainsWithPositions(pyAst):
            if chainWithPosition and \
               chainWithPosition.var[0] in ['staticmethod', 'property', '__inline_fora']:
                continue

            subchain, resolution, position = self._resolveChainInPyObject(
                chainWithPosition, pyObject, pyAst
                )
            resolutions[subchain] = (resolution, position)

        return resolutions

